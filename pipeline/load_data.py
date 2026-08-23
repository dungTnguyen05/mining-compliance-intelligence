import json
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

from clean_data import (
    clean_electricity_meter_readings,
    clean_emission_factors,
    clean_fuel_deliveries,
    clean_incident_register,
    clean_suppliers,
)

from validate_data import (
    validate_incident_register,
    validate_suppliers,
)


load_dotenv()

DATA_DIR = Path("data/raw")
SCHEMA_PATH = Path("database/schema.sql")


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def create_schema(connection):
    # execute database schema
    schema_sql = SCHEMA_PATH.read_text()

    with connection.cursor() as cursor:
        cursor.execute(schema_sql)

    connection.commit()


def load_cleaned_data():
    # load raw datasets
    electricity = pd.read_csv(
        DATA_DIR / "electricity_meter_readings.csv"
    )
    emission_factors = pd.read_csv(
        DATA_DIR / "emission_factors.csv"
    )
    fuel_deliveries = pd.read_csv(
        DATA_DIR / "fuel_deliveries.csv"
    )
    incident_register = pd.read_csv(
        DATA_DIR / "incident_register.csv"
    )
    suppliers = pd.read_csv(
        DATA_DIR / "suppliers.csv"
    )

    # clean datasets
    electricity = clean_electricity_meter_readings(electricity)
    emission_factors = clean_emission_factors(emission_factors)
    fuel_deliveries = clean_fuel_deliveries(fuel_deliveries)
    incident_register = clean_incident_register(incident_register)
    suppliers = clean_suppliers(suppliers)

    return (
        electricity,
        emission_factors,
        fuel_deliveries,
        incident_register,
        suppliers,
    )


def insert_electricity(connection, electricity):
    # insert unique electricity meters
    meters = (
        electricity[
            ["meter_id", "meter_description"]
        ]
        .drop_duplicates()
    )

    with connection.cursor() as cursor:
        for _, row in meters.iterrows():
            cursor.execute(
                """
                INSERT INTO electricity_meters (
                    meter_id,
                    meter_description
                )
                VALUES (%s, %s)
                ON CONFLICT (meter_id) DO NOTHING
                """,
                (
                    row["meter_id"],
                    row["meter_description"],
                ),
            )

        # insert electricity readings
        for _, row in electricity.iterrows():
            cursor.execute(
                """
                INSERT INTO electricity_readings (
                    meter_id,
                    period,
                    consumption_kwh
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (meter_id, period) DO NOTHING
                """,
                (
                    row["meter_id"],
                    row["period"].date(),
                    row["consumption"],
                ),
            )

    connection.commit()


def insert_emission_factors(connection, emission_factors):
    with connection.cursor() as cursor:
        for _, row in emission_factors.iterrows():
            cursor.execute(
                """
                INSERT INTO emission_factors (
                    activity,
                    scope,
                    unit,
                    kg_co2e_per_unit,
                    source
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (activity) DO NOTHING
                """,
                (
                    row["activity"],
                    int(row["scope"]),
                    row["unit"],
                    row["kg_co2e_per_unit"],
                    row["source"],
                ),
            )

    connection.commit()


def insert_fuel_deliveries(connection, fuel_deliveries):
    with connection.cursor() as cursor:
        for _, row in fuel_deliveries.iterrows():
            cursor.execute(
                """
                INSERT INTO fuel_deliveries (
                    invoice_no,
                    delivery_date,
                    fuel_type,
                    quantity_litres,
                    cost_aud,
                    site_area
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    row["invoice_no"],
                    row["delivery_date"].date(),
                    row["fuel_type"],
                    row["quantity"],
                    row["cost_aud"],
                    row["site_area"],
                ),
            )

    connection.commit()


def insert_incidents(connection, incident_register):
    with connection.cursor() as cursor:
        for _, row in incident_register.iterrows():
            cursor.execute(
                """
                INSERT INTO incidents (
                    incident_id,
                    incident_date,
                    location,
                    type_code,
                    severity,
                    description
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    row["incident_id"],
                    row["incident_date"].date(),
                    row["location"],
                    row["type_code"],
                    row["severity"],
                    row["description"],
                ),
            )

    connection.commit()


def insert_suppliers(connection, suppliers):
    with connection.cursor() as cursor:
        for _, row in suppliers.iterrows():
            abn = None if pd.isna(row["abn"]) else row["abn"]

            cursor.execute(
                """
                INSERT INTO suppliers (
                    supplier_name,
                    abn,
                    category,
                    fy_spend_aud
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    row["supplier_name"],
                    abn,
                    row["category"],
                    row["fy_spend_aud"],
                ),
            )

    connection.commit()


def insert_data_quality_issues(
    connection,
    incident_register,
    suppliers,
):
    # collect unresolved flagged issues
    issues = []

    for issue in validate_incident_register(incident_register):
        if issue.get("action") == "flagged":
            issues.append({
                "dataset": "incident_register",
                **issue,
            })

    for issue in validate_suppliers(suppliers):
        if issue.get("action") == "flagged":
            issues.append({
                "dataset": "suppliers",
                **issue,
            })

    with connection.cursor() as cursor:
        for issue in issues:
            record_key = (
                issue.get("incident_id")
                or issue.get("abn")
                or issue.get("supplier_name")
            )

            cursor.execute(
                """
                INSERT INTO data_quality_issues (
                    dataset,
                    issue_type,
                    action,
                    record_key,
                    details
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    issue["dataset"],
                    issue["issue"],
                    issue["action"],
                    record_key,
                    json.dumps(issue),
                ),
            )

    connection.commit()


def main():
    connection = get_connection()

    try:
        print("Connected to PostgreSQL.")

        create_schema(connection)

        (
            electricity,
            emission_factors,
            fuel_deliveries,
            incident_register,
            suppliers,
        ) = load_cleaned_data()

        insert_electricity(connection, electricity)
        insert_emission_factors(connection, emission_factors)
        insert_fuel_deliveries(connection, fuel_deliveries)
        insert_incidents(connection, incident_register)
        insert_suppliers(connection, suppliers)

        insert_data_quality_issues(
            connection,
            incident_register,
            suppliers,
        )

        print("Data loaded successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
