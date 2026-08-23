from pathlib import Path
import pandas as pd

from clean_data import (
    clean_electricity_meter_readings,
    clean_emission_factors,
    clean_fuel_deliveries,
    clean_incident_register,
    clean_suppliers,
)

from validate_data import (
    validate_electricity_meter_readings,
    validate_emission_factors,
    validate_fuel_deliveries,
    validate_incident_register,
    validate_suppliers,
    validate_fuel_emission_factors,
    validate_electricity_emission_factor,
    validate_reporting_periods,
)

DATA_DIR = Path("data/raw")

def main():
    # load raw datasets
    electricity = pd.read_csv(DATA_DIR/"electricity_meter_readings.csv")
    emission_factors = pd.read_csv(DATA_DIR/"emission_factors.csv")
    fuel_deliveries = pd.read_csv(DATA_DIR/"fuel_deliveries.csv")
    incident_register = pd.read_csv(DATA_DIR/"incident_register.csv")
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

    # run individual dataset validations
    validation_results = {
        "electricity_meter_readings": (
            validate_electricity_meter_readings(electricity)
        ),
        "emission_factors": (
            validate_emission_factors(emission_factors)
        ),
        "fuel_deliveries": (
            validate_fuel_deliveries(fuel_deliveries)
        ),
        "incident_register": (
            validate_incident_register(incident_register)
        ),
        "suppliers": (
            validate_suppliers(suppliers)
        ),
    }

    # run cross-dataset validations
    validation_results["fuel_emission_factors"] = (
        validate_fuel_emission_factors(
            fuel_deliveries,
            emission_factors,
        )
    )

    validation_results["electricity_emission_factor"] = (
        validate_electricity_emission_factor(
            electricity,
            emission_factors,
        )
    )

    validation_results["reporting_periods"] = (
        validate_reporting_periods(
            electricity,
            fuel_deliveries,
            incident_register,
        )
    )

    # print data quality corrections
    print("\n" + "=" * 80)
    print("data_quality_events")
    print("=" * 80)

    if not data_quality_events:
        print("No corrections made.")
    else:
        for event in data_quality_events:
            print(event)

    # print validation results
    for dataset, issues in validation_results.items():
        print("\n" + "=" * 80)
        print(dataset)
        print("=" * 80)

        if not issues:
            print("No issues found.")
            continue

        for issue in issues:
            print(issue)

if __name__ == "__main__":
    main()
