def validate_electricity_meter_readings(df):
    issues = []

    # check required columns
    required_columns = {
        "meter_id",
        "meter_description",
        "period",
        "consumption",
        "unit",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        issues.append({
            "issue": "missing required columns",
            "details": sorted(missing_columns),
        })
        return issues

    # check missing values
    for column in required_columns:
        missing_count = df[column].isna().sum()

        if missing_count > 0:
            issues.append({
                "issue": "missing values",
                "field": column,
                "count": int(missing_count),
            })

    # check duplicate meter-period records
    duplicate_mask = df.duplicated(
        subset=["meter_id", "period"],
        keep=False,
    )

    if duplicate_mask.any():
        issues.append({
            "issue": "duplicate meter-period records",
            "count": int(duplicate_mask.sum()),
        })

    # check meter id and description consistency
    description_counts = (
        df.groupby("meter_id")["meter_description"]
        .nunique()
    )

    inconsistent_meters = description_counts[
        description_counts > 1
    ]

    for meter_id in inconsistent_meters.index:
        issues.append({
            "issue": "inconsistent meter description",
            "meter_id": meter_id,
            "descriptions": (
                df.loc[
                    df["meter_id"] == meter_id,
                    "meter_description"
                ]
                .unique()
                .tolist()
            ),
        })

    # check non-positive consumption
    invalid_consumption = df["consumption"] <= 0

    if invalid_consumption.any():
        issues.append({
            "issue": "non-positive consumption",
            "count": int(invalid_consumption.sum()),
        })

    # check unexpected units
    invalid_units = ~df["unit"].isin(["kWh"])

    if invalid_units.any():
        issues.append({
            "issue": "unexpected electricity unit",
            "values": (
                df.loc[invalid_units, "unit"]
                .dropna()
                .unique()
                .tolist()
            ),
        })

    # detect large month-to-month changes per meter
    ordered = df.sort_values(
        ["meter_id", "period"]
    ).copy()

    ordered["previous_consumption"] = (
        ordered.groupby("meter_id")["consumption"].shift(1)
    )

    ordered["change_ratio"] = (
        ordered["consumption"]
        / ordered["previous_consumption"]
    )

    abnormal_change = (
        (ordered["change_ratio"] < 0.2)
        | (ordered["change_ratio"] > 5)
    )

    for _, row in ordered[abnormal_change].iterrows():
        issues.append({
            "issue": "large consumption change",
            "meter_id": row["meter_id"],
            "period": row["period"].strftime("%Y-%m"),
            "previous_consumption": row["previous_consumption"],
            "consumption": row["consumption"],
            "change_ratio": row["change_ratio"],
        })

    return issues

def validate_emission_factors(df):
    ...

def validate_fuel_deliveries(df):
    ...

def validate_incident_register(df):
    ...

def validate_suppliers(df):
    ...
