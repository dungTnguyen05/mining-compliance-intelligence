from pathlib import Path
import pandas as pd
DATA_DIR = Path("data/raw")

def inspect_csv(file_path: Path):
    df = pd.read_csv(file_path)

    print("\n" + "=" * 80)
    print(f"File: {file_path.name}")
    print("=" * 80)

    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nData types:")
    print(df.dtypes)

    print("\nMissing values:")
    missing = df.isna().sum()
    print(missing[missing > 0])

    print(f"\nDuplicate rows: {df.duplicated().sum()}")

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nSummary:")
    print(df.describe(include="all").transpose())

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
    