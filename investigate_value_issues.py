"""
Investigate value unit issues in 2017-2020 data.
"""

import pandas as pd
from pathlib import Path

def check_raw_values():
    """Check raw CSV values for problematic years."""

    print("="*60)
    print("Investigating Value Column Issues (2017-2020)")
    print("="*60)

    for year in [2017, 2018, 2019, 2020]:
        print(f"\n{'='*60}")
        print(f"Year: {year}")
        print(f"{'='*60}")

        file_path = Path(f"data/{year}.csv")
        df = pd.read_csv(file_path)

        # Show first few rows
        print(f"\nFirst 5 rows of data:")
        print(df.head())

        # Show column names
        print(f"\nColumns:")
        print(list(df.columns))

        # Find value column
        value_col = None
        for col in df.columns:
            if 'value' in col.lower() or 'Value' in col:
                value_col = col
                break

        if value_col:
            print(f"\nValue column: '{value_col}'")
            print(f"Sample values:")
            print(df[value_col].head(20))
            print(f"\nStats:")
            print(df[value_col].describe())

            # Check if values look like pounds or thousands
            mean_val = df[value_col].mean()
            print(f"\nMean value: {mean_val:,.2f}")

            if mean_val < 100:
                print("⚠️  Values appear to be in THOUSANDS (£000s)")
            elif mean_val > 1000:
                print("⚠️  Values appear to be in POUNDS (£)")
            else:
                print("❓ Unclear - values in intermediate range")


if __name__ == "__main__":
    check_raw_values()
