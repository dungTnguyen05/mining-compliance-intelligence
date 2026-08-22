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
    issues = []

    # check required columns
    required_columns = {
        "activity",
        "scope",
        "unit",
        "kg_co2e_per_unit",
        "source",
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

    # check duplicate activities
    duplicate_activities = df["activity"].duplicated(
        keep=False
    )

    if duplicate_activities.any():
        issues.append({
            "issue": "duplicate emission factor activity",
            "activities": (
                df.loc[duplicate_activities, "activity"]
                .unique()
                .tolist()
            ),
        })

    # check valid scope values
    invalid_scope = ~df["scope"].isin([1, 2, 3])

    if invalid_scope.any():
        issues.append({
            "issue": "invalid emission scope",
            "values": (
                df.loc[invalid_scope, "scope"]
                .dropna()
                .unique()
                .tolist()
            ),
        })

    # check emission factors are positive
    invalid_factor = df["kg_co2e_per_unit"] <= 0

    if invalid_factor.any():
        issues.append({
            "issue": "non-positive emission factor",
            "count": int(invalid_factor.sum()),
        })

    # check units are present
    invalid_unit = (
        df["unit"].isna()
        | (df["unit"] == "")
    )

    if invalid_unit.any():
        issues.append({
            "issue": "missing emission factor unit",
            "count": int(invalid_unit.sum()),
        })

    return issues

def validate_fuel_deliveries(df):
    issues = []

    # check required columns
    required_columns = {
        "invoice_no",
        "delivery_date",
        "fuel_type",
        "quantity",
        "unit",
        "cost_aud",
        "site_area",
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

    # check exact duplicate records
    duplicate_rows = df.duplicated(
        keep=False
    )

    if duplicate_rows.any():
        issues.append({
            "issue": "exact duplicate records",
            "count": int(duplicate_rows.sum()),
        })

    # check duplicate invoice numbers
    duplicate_invoices = df["invoice_no"].duplicated(
        keep=False
    )

    if duplicate_invoices.any():
        issues.append({
            "issue": "duplicate invoice numbers",
            "invoice_numbers": (
                df.loc[duplicate_invoices, "invoice_no"]
                .dropna()
                .unique()
                .tolist()
            ),
        })

    # check non-positive quantities
    invalid_quantity = df["quantity"] <= 0

    if invalid_quantity.any():
        for _, row in df[invalid_quantity].iterrows():
            issues.append({
                "issue": "non-positive fuel quantity",
                "invoice_no": row["invoice_no"],
                "quantity": row["quantity"],
            })

    # check unexpected fuel units after cleaning
    invalid_units = ~df["unit"].isin(["L"])

    if invalid_units.any():
        issues.append({
            "issue": "unexpected fuel unit",
            "values": (
                df.loc[invalid_units, "unit"]
                .dropna()
                .unique()
                .tolist()
            ),
        })

    # check invalid delivery dates
    invalid_dates = df["delivery_date"].isna()

    if invalid_dates.any():
        issues.append({
            "issue": "invalid delivery date",
            "count": int(invalid_dates.sum()),
        })

    # check non-positive costs
    invalid_cost = df["cost_aud"] <= 0

    if invalid_cost.any():
        for _, row in df[invalid_cost].iterrows():
            issues.append({
                "issue": "non-positive fuel cost",
                "invoice_no": row["invoice_no"],
                "cost_aud": row["cost_aud"],
            })

    return issues

def validate_incident_register(df):
    ...

def validate_suppliers(df):
    ...
