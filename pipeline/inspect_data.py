from pathlib import Path

import pandas as pd

DATA_DIR = Path("data/raw")


def inspect_basic(df: pd.DataFrame):
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nData types:")
    print(df.dtypes)

    print("\nMissing values:")
    missing = df.isna().sum()
    if missing.sum() == 0:
        print("None")
    else:
        print(missing[missing > 0])

    print(f"\nDuplicate rows: {df.duplicated().sum()}")

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nSummary:")
    print(df.describe(include="all").transpose())


def inspect_unique_values(df: pd.DataFrame):
    print("\nUnique values:")

    for column in df.columns:
        unique_count = df[column].nunique(dropna=False)

        print(f"\n{column}: {unique_count} unique values")

        # Only print actual values when there are not too many
        if unique_count <= 20:
            print(df[column].value_counts(dropna=False))


def inspect_numeric_columns(df: pd.DataFrame):
    numeric_columns = df.select_dtypes(include="number").columns

    if len(numeric_columns) == 0:
        return

    print("\nNumeric ranges:")

    for column in numeric_columns:
        print(
            f"{column}: "
            f"min={df[column].min()}, "
            f"max={df[column].max()}, "
            f"median={df[column].median()}"
        )


def inspect_csv(file_path: Path):
    df = pd.read_csv(file_path)

    print("\n" + "=" * 80)
    print(f"File: {file_path.name}")
    print("=" * 80)

    inspect_basic(df)
    inspect_unique_values(df)
    inspect_numeric_columns(df)


def main():
    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {DATA_DIR}")
        return

    print(f"Found {len(csv_files)} CSV files.")

    for file_path in csv_files:
        inspect_csv(file_path)


if __name__ == "__main__":
    main()
