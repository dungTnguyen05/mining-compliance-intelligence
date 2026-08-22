def is_valid_abn(abn):
    if pd.isna(abn):
        return False

    abn = str(abn)

    # check abn has exactly 11 digits
    if len(abn) != 11 or not abn.isdigit():
        return False

    digits = [int(digit) for digit in abn]

    # subtract one from the first digit
    digits[0] -= 1

    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]

    total = sum(
        digit * weight
        for digit, weight in zip(digits, weights)
    )

    return total % 89 == 0

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
    issues = []

    # check required columns
    required_columns = {
        "incident_id",
        "incident_date",
        "location",
        "type_code",
        "severity",
        "description",
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
        if df[column].dtype == "object":
            missing_mask = (
                df[column].isna()
                | (df[column] == "")
            )
        else:
            missing_mask = df[column].isna()

        missing_count = missing_mask.sum()

        if missing_count > 0:
            issues.append({
                "issue": "missing values",
                "field": column,
                "count": int(missing_count),
            })

    # check duplicate incident ids
    duplicate_ids = df["incident_id"].duplicated(
        keep=False
    )

    if duplicate_ids.any():
        for incident_id in (
            df.loc[duplicate_ids, "incident_id"]
            .dropna()
            .unique()
        ):
            matching_rows = df[
                df["incident_id"] == incident_id
            ]

            issues.append({
                "issue": "duplicate incident id",
                "incident_id": incident_id,
                "count": len(matching_rows),
            })

    # check invalid incident dates
    invalid_dates = df["incident_date"].isna()

    if invalid_dates.any():
        issues.append({
            "issue": "invalid incident date",
            "count": int(invalid_dates.sum()),
        })

    # check severity values
    valid_severities = {
        "Low",
        "Medium",
        "High",
    }

    invalid_severity = (
        df["severity"].notna()
        & ~df["severity"].isin(valid_severities)
    )

    if invalid_severity.any():
        issues.append({
            "issue": "unexpected severity",
            "values": (
                df.loc[invalid_severity, "severity"]
                .unique()
                .tolist()
            ),
        })

    return issues

def validate_suppliers(df):
    issues = []

    # check required columns
    required_columns = {
        "supplier_name",
        "abn",
        "category",
        "fy_spend_aud",
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
        if df[column].dtype == "object":
            missing_mask = (
                df[column].isna()
                | (df[column] == "")
            )
        else:
            missing_mask = df[column].isna()

        missing_count = missing_mask.sum()

        if missing_count > 0:
            issues.append({
                "issue": "missing values",
                "field": column,
                "count": int(missing_count),
            })

    # check invalid abns
    invalid_abn = (
        df["abn"].notna()
        & ~df["abn"].apply(is_valid_abn)
    )

    if invalid_abn.any():
        for _, row in df[invalid_abn].iterrows():
            issues.append({
                "issue": "invalid abn",
                "supplier_name": row["supplier_name"],
                "abn": row["abn"],
            })

    # check duplicate abns
    duplicate_abn = (
        df["abn"].notna()
        & df["abn"].duplicated(keep=False)
    )

    if duplicate_abn.any():
        for abn in (
            df.loc[duplicate_abn, "abn"]
            .dropna()
            .unique()
        ):
            suppliers = (
                df.loc[
                    df["abn"] == abn,
                    "supplier_name"
                ]
                .unique()
                .tolist()
            )

            issues.append({
                "issue": "duplicate abn",
                "abn": abn,
                "supplier_names": suppliers,
            })

    # check non-positive spend
    invalid_spend = df["fy_spend_aud"] <= 0

    if invalid_spend.any():
        for _, row in df[invalid_spend].iterrows():
            issues.append({
                "issue": "non-positive supplier spend",
                "supplier_name": row["supplier_name"],
                "fy_spend_aud": row["fy_spend_aud"],
            })

    return issues

#--------------------------------------------------------------------------------
# CROSS-DATASET VALIDATIONS

# check each fuel type has a matching emission factor and unit
# example: Diesel + L must match Diesel factor + L
def validate_fuel_emission_factors(fuel_deliveries, emission_factors):
    issues = []

    # map fuel types to emission factor activities
    activity_mapping = {
        "Diesel": "Diesel combustion (stationary & transport)",
        "Petrol (ULP)": "Petrol (ULP) combustion",
    }

    # check each fuel type against emission factors
    for fuel_type in fuel_deliveries["fuel_type"].dropna().unique():
        activity = activity_mapping.get(fuel_type)

      # check fuel type has a known mapping
        if activity is None:
            issues.append({
                "issue": "unmapped fuel type",
                "fuel_type": fuel_type,
            })
            continue

        # find matching emission factor
        matching_factor = emission_factors[
            emission_factors["activity"] == activity
        ]

        # check matching emission factor exists
        if matching_factor.empty:
            issues.append({
                "issue": "missing emission factor",
                "fuel_type": fuel_type,
                "activity": activity,
            })
            continue

        # get units used for this fuel type
        fuel_units = set(
            fuel_deliveries.loc[
                fuel_deliveries["fuel_type"] == fuel_type,
                "unit",
            ].dropna()
        )

        # get units used by the emission factor
        factor_units = set(
            matching_factor["unit"].dropna()
        )

        # check fuel and emission factor units match
        if fuel_units != factor_units:
            issues.append({
                "issue": "fuel emission factor unit mismatch",
                "fuel_type": fuel_type,
                "fuel_units": sorted(fuel_units),
                "factor_units": sorted(factor_units),
            })

    return issues

# check electricity readings have a matching grid emission factor and unit
# example: electricity + kWh must match grid factor + kWh
def validate_electricity_emission_factor(electricity_meter_readings, emission_factors):
    issues = []

    # find grid electricity emission factor
    grid_factor = emission_factors[
        emission_factors["activity"]
        == "Grid electricity - Queensland"
    ]

    # check grid electricity emission factor exists
    if grid_factor.empty:
        issues.append({
            "issue": "missing grid electricity emission factor",
        })
        return issues

    # get electricity units
    electricity_units = set(
        electricity_meter_readings["unit"]
        .dropna()
        .unique()
    )

    # get emission factor units
    factor_units = set(
        grid_factor["unit"]
        .dropna()
        .unique()
    )

    # check electricity and emission factor units match
    if electricity_units != factor_units:
        issues.append({
            "issue": "electricity emission factor unit mismatch",
            "electricity_units": sorted(electricity_units),
            "factor_units": sorted(factor_units),
        })

    return issues

# check fuel deliveries and incidents fall within Jan 2025 to Jun 2026
# example: a record dated Jul 2026 should be flagged
def validate_reporting_periods(electricity_meter_readings, fuel_deliveries, incident_register):
    issues = []

    # get reporting period from electricity data
    start_date = electricity_meter_readings["period"].min()
    end_date = (
        electricity_meter_readings["period"].max()
        + pd.offsets.MonthEnd(1)
    )

    # check fuel delivery dates against reporting period
    fuel_outside_period = (
        fuel_deliveries["delivery_date"].notna()
        & (
            (fuel_deliveries["delivery_date"] < start_date)
            | (fuel_deliveries["delivery_date"] > end_date)
        )
    )

    if fuel_outside_period.any():
        issues.append({
            "issue": "fuel deliveries outside reporting period",
            "count": int(fuel_outside_period.sum()),
        })

    # check incident dates against reporting period
    incidents_outside_period = (
        incident_register["incident_date"].notna()
        & (
            (incident_register["incident_date"] < start_date)
            | (incident_register["incident_date"] > end_date)
        )
    )

    if incidents_outside_period.any():
        issues.append({
            "issue": "incidents outside reporting period",
            "count": int(incidents_outside_period.sum()),
        })

    return issues
