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

from incident_source import add_incident_source_identity
from validate_data import (
    validate_incident_register,
    validate_suppliers,
)

load_dotenv()

DATA_DIR = Path("data/raw")
SCHEMA_PATH = Path("database/schema.sql")

# database connection
def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

# database setup
def create_schema(connection):
    # create database tables if they do not already exist
    schema_sql = SCHEMA_PATH.read_text()

    with connection.cursor() as cursor:
        cursor.execute(schema_sql)

    connection.commit()

def clear_existing_data(connection):
    # clear previously loaded data before inserting the current cleaned dataset
    with connection.cursor() as cursor:
        cursor.execute(
            """
            TRUNCATE TABLE
                data_quality_issues,
                electricity_readings,
                electricity_meters,
                emission_factors,
                fuel_deliveries,
                incident_ai_findings,
                incidents,
                suppliers
            RESTART IDENTITY CASCADE
            """
        )

    connection.commit()

# load and clean datasets
def load_cleaned_data():
    # load raw datasets
    electricity = pd.read_csv(DATA_DIR/"electricity_meter_readings.csv")
    emission_factors = pd.read_csv(DATA_DIR/"emission_factors.csv")
    fuel_deliveries = pd.read_csv(DATA_DIR/"fuel_deliveries.csv")
    incident_register = pd.read_csv(
        DATA_DIR/"incident_register.csv",
        dtype=str,
        keep_default_na=False,
    )
    incident_register = add_incident_source_identity(incident_register)
    suppliers = pd.read_csv(DATA_DIR/"suppliers.csv")

    # clean datasets
    electricity, electricity_events = clean_electricity_meter_readings(electricity)
    emission_factors, emission_factor_events = clean_emission_factors(emission_factors)
    fuel_deliveries, fuel_events = clean_fuel_deliveries(fuel_deliveries)
    incident_register, incident_events = clean_incident_register(incident_register)
    suppliers, supplier_events = clean_suppliers(suppliers)

    # merge data quality events from all datasets
    data_quality_events = (
        electricity_events
        + emission_factor_events
        + fuel_events
        + incident_events
        + supplier_events
    )

    return (
        electricity,
        emission_factors,
        fuel_deliveries,
        incident_register,
        suppliers,
        data_quality_events,
    )

# insert electricity data
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
                """,
                (
                    row["meter_id"],
                    row["period"].date(),
                    row["consumption"],
                ),
            )

    connection.commit()

# insert emission factors
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

# insert fuel deliveries
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

# insert incidents
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
                    description,
                    source_row,
                    source_record_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["incident_id"],
                    row["incident_date"].date(),
                    row["location"],
                    row["type_code"],
                    row["severity"],
                    row["description"],
                    int(row["source_row"]),
                    row["source_record_hash"],
                ),
            )

    connection.commit()

def enforce_incident_source_constraints(connection):
    # enforce source identity after existing databases have been reloaded
    with connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE incidents
                ALTER COLUMN source_row SET NOT NULL,
                ALTER COLUMN source_record_hash SET NOT NULL
            """
        )

    connection.commit()

# insert suppliers
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

# insert data quality issues
def insert_data_quality_issues(connection, incident_register, suppliers, data_quality_events):
    # merge fixed corrections with unresolved flagged issues
    issues = data_quality_events.copy()

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
                issue.get("record_key")
                or issue.get("incident_id")
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

        # create tables if they do not already exist
        create_schema(connection)

        # load and clean raw datasets
        (
            electricity,
            emission_factors,
            fuel_deliveries,
            incident_register,
            suppliers,
            data_quality_events,
        ) = load_cleaned_data()

        # replace existing loaded data with the current cleaned dataset
        clear_existing_data(connection)

        # insert cleaned datasets
        insert_electricity(connection, electricity)
        insert_emission_factors(connection, emission_factors)
        insert_fuel_deliveries(connection, fuel_deliveries)
        insert_incidents(connection, incident_register)
        enforce_incident_source_constraints(connection)
        insert_suppliers(connection, suppliers)

        # insert fixed and unresolved data quality issues
        insert_data_quality_issues(connection, incident_register, suppliers, data_quality_events)

        print("Data loaded successfully.")

    finally:
        connection.close()

if __name__ == "__main__":
    main()
