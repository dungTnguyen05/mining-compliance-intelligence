import pandas as pd

def clean_electricity_meter_readings(df):
    df = df.copy()

    # normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # trim leading and trailing whitespace from string values
    string_columns = df.select_dtypes(include="object").columns
    for column in string_columns:
        df[column] = df[column].str.strip()

    # parse reporting period
    df["period"] = pd.to_datetime(
        df["period"],
        format="%Y-%m",
        errors="coerce"
    )

    # ensure consumption is numeric
    df["consumption"] = pd.to_numeric(
        df["consumption"],
        errors="coerce"
    )

    # data correction 1: MTR-07 scale adjustment
    # decision based on the sustained 1000x drop from Oct 2025 onward
    mtr07_scale_mask = (
        (df["meter_id"] == "MTR-07")
        & (df["period"] >= pd.Timestamp("2025-10-01"))
    )

    df.loc[mtr07_scale_mask, "consumption"] = (
        df.loc[mtr07_scale_mask, "consumption"] * 1000
    )

    # sort records consistently
    df = df.sort_values(
        ["meter_id", "period"]
    ).reset_index(drop=True)

    return df

def clean_emission_factors(df):
    df = df.copy()

    # normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # trim leading and trailing whitespace from string values
    string_columns = df.select_dtypes(include="object").columns
    for column in string_columns:
        df[column] = df[column].str.strip()

    # ensure scope is numeric
    df["scope"] = pd.to_numeric(
        df["scope"],
        errors="coerce"
    )

    # ensure emission factor is numeric
    df["kg_co2e_per_unit"] = pd.to_numeric(
        df["kg_co2e_per_unit"],
        errors="coerce"
    )

    return df

def clean_fuel_deliveries(df):
    df = df.copy()

    # normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[()]", "", regex=True)
    )

    # trim leading and trailing whitespace from string values
    string_columns = df.select_dtypes(include="object").columns
    for column in string_columns:
        df[column] = df[column].str.strip()

    # parse delivery dates with mixed formats
    delivery_dates = df["delivery_date"].astype("string").str.strip()

    df["delivery_date"] = pd.to_datetime(
        delivery_dates,
        format="mixed",
        dayfirst=True,
        errors="coerce"
    )

    # use the first day for month-only dates, e.g. Oct-25 -> 2025-10-01
    month_year_mask = (
        df["delivery_date"].isna()
        & delivery_dates.str.match(r"^[A-Za-z]{3}-\d{2}$", na=False)
    )

    df.loc[month_year_mask, "delivery_date"] = pd.to_datetime(
        delivery_dates[month_year_mask],
        format="%b-%y",
        errors="coerce"
    )

    # ensure quantity is numeric
    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    )

    # normalize unit labels
    df["unit"] = df["unit"].str.lower()

    # convert kilolitres to litres
    kl_mask = df["unit"] == "kl"

    df.loc[kl_mask, "quantity"] = (
        df.loc[kl_mask, "quantity"] * 1000
    )

    # standardize all litre units
    df["unit"] = df["unit"].replace({
        "l": "L",
        "litres": "L",
        "kl": "L"
    })

    # remove currency formatting
    df["cost_aud"] = (
        df["cost_aud"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )

    # ensure cost is numeric
    df["cost_aud"] = pd.to_numeric(
        df["cost_aud"],
        errors="coerce"
    )

    # data correction 2: remove exact duplicate fuel delivery records
    # identical rows would otherwise double-count quantity, cost, and emissions
    df = df.drop_duplicates().reset_index(drop=True)

    # data correction 3: correct negative values for INV-41777
    # decision based on both values appearing to have incorrect negative signs
    inv_41777_mask = df["invoice_no"] == "INV-41777"

    df.loc[inv_41777_mask, "quantity"] = (
        df.loc[inv_41777_mask, "quantity"].abs()
    )

    df.loc[inv_41777_mask, "cost_aud"] = (
        df.loc[inv_41777_mask, "cost_aud"].abs()
    )

    return df

def clean_incident_register(df):
    df = df.copy()

    # normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # trim leading and trailing whitespace from string values
    string_columns = df.select_dtypes(include="object").columns
    for column in string_columns:
        df[column] = df[column].str.strip()

    # parse incident dates
    df["incident_date"] = pd.to_datetime(
        df["incident_date"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    # normalize severity values
    df["severity"] = df["severity"].replace({
        "1": "Low",
        "2": "Medium",
        "3": "High"
    })

    # sort records consistently
    df = df.sort_values(
        ["incident_date", "incident_id"]
    ).reset_index(drop=True)

    return df

def clean_suppliers(df):
    df = df.copy()

    # normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # trim leading and trailing whitespace from string values
    string_columns = df.select_dtypes(include="object").columns
    for column in string_columns:
        df[column] = df[column].str.strip()

    # normalize abn formatting
    df["abn"] = (
        df["abn"]
        .str.replace(" ", "", regex=False)
    )

    # ensure spend is numeric
    df["fy_spend_aud"] = pd.to_numeric(
        df["fy_spend_aud"],
        errors="coerce"
    )

    return df
