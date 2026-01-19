"""
Standardize MMO landing data across all years (2014-2024).

Handles:
- Column name variations
- Nationality format inconsistencies ("UK - England" → "England")
- Value unit differences (2019-2020 use £, others use £000s)
- Missing gear/species data in earlier years
"""

import pandas as pd
from pathlib import Path
import sqlite3

# Standard column mapping - map various column names to our standard schema
COLUMN_MAPPINGS = {
    # Month columns
    'Month Landed': 'month',
    'Month': 'month',

    # Port columns
    'Port of Landing': 'port',
    'Port of landing': 'port',
    'Port NUTS 2 area': 'port_nuts2',

    # Nationality columns
    'Port Nationality': 'port_nationality',
    'Vessel Nationality': 'vessel_nationality',
    'Vessel nationality': 'vessel_nationality',

    # Vessel characteristics
    'Length Group': 'length_group',

    # Gear
    'Gear category': 'gear_category',

    # Species columns
    'Species': 'species_name',
    'Species name': 'species_name',
    'Species code': 'species_code',
    'Species Group': 'species_group',
    'Species group': 'species_group',

    # Weight and value columns
    'Live weight (tonnes)': 'live_weight_tonnes',
    'Sum of Live weight (tonnes)': 'live_weight_tonnes',
    'Live Weight (tonnes)': 'live_weight_tonnes',

    'Landed weight (tonnes)': 'landed_weight_tonnes',
    'Sum of Landed weight (tonnes)': 'landed_weight_tonnes',
    'Landed Weight (tonnes)': 'landed_weight_tonnes',

    'Value(£000s)': 'value_thousands',
    'Sum of Value(£)': 'value_pounds',  # Special case - needs conversion
    'Value (£000s)': 'value_thousands',

    # Year
    'Year': 'year',
}

# Nationality standardization - remove "UK -" prefix and standardize
def standardize_nationality(value):
    """Convert various nationality formats to standard names."""
    if pd.isna(value):
        return value

    value = str(value).strip()

    # Remove "UK -" prefix
    if value.startswith("UK - "):
        value = value[5:]  # Remove "UK - "

    # Handle specific cases
    replacements = {
        "Faeroe Islands": "Faroe Islands",
        "FRO": "Faroe Islands",
    }

    return replacements.get(value, value)


def load_and_standardize_year(year: int, verbose: bool = True) -> pd.DataFrame:
    """Load and standardize data for a single year."""

    file_path = Path(f"data/{year}.csv")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if verbose:
        print(f"\nProcessing {year}...")

    # Read CSV
    df = pd.read_csv(file_path)

    if verbose:
        print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

    # Drop unnamed columns (like "Unnamed: 11")
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Drop "Change" columns from 2023 data
    change_cols = [col for col in df.columns if col.startswith('Change ')]
    if change_cols:
        df = df.drop(columns=change_cols)
        if verbose:
            print(f"  Dropped {len(change_cols)} 'Change' columns")

    # Rename columns to standard names
    df = df.rename(columns=COLUMN_MAPPINGS)

    # Add year column if not present
    if 'year' not in df.columns:
        df['year'] = year

    # Handle value unit inconsistencies (MMO data has misleading labels)
    # 2017-2018: Column labeled "Value(£000s)" but data is actually in POUNDS
    if year in [2017, 2018] and 'value_thousands' in df.columns:
        df['value_thousands'] = df['value_thousands'] / 1000
        if verbose:
            print(f"  Corrected mislabeled values: converted £ to £000s")

    # 2019-2020: Column labeled "Sum of Value(£)" but data is actually in THOUSANDS
    # The values are already in the correct unit, just rename
    if 'value_pounds' in df.columns:
        # Despite the label, these are already in thousands
        df['value_thousands'] = df['value_pounds']
        df = df.drop(columns=['value_pounds'])
        if verbose:
            print(f"  Renamed mislabeled value column (was already in £000s)")

    # Standardize nationalities
    if 'port_nationality' in df.columns:
        df['port_nationality'] = df['port_nationality'].apply(standardize_nationality)

    if 'vessel_nationality' in df.columns:
        df['vessel_nationality'] = df['vessel_nationality'].apply(standardize_nationality)

    # Ensure consistent column order and add missing columns with NULL
    standard_columns = [
        'year',
        'month',
        'port',
        'port_nuts2',
        'port_nationality',
        'vessel_nationality',
        'length_group',
        'gear_category',
        'species_code',
        'species_name',
        'species_group',
        'live_weight_tonnes',
        'landed_weight_tonnes',
        'value_thousands',
    ]

    # Add missing columns as NULL
    for col in standard_columns:
        if col not in df.columns:
            df[col] = None

    # Select only standard columns in standard order
    df = df[standard_columns]

    if verbose:
        print(f"  Standardized to {len(df.columns)} columns")

    return df


def standardize_all_years(output_path: str = None, verbose: bool = True):
    """
    Load and standardize all years, optionally saving to SQLite database.

    Args:
        output_path: Path to SQLite database. If None, returns DataFrame
        verbose: Print progress messages

    Returns:
        Combined DataFrame if output_path is None
    """

    all_data = []

    for year in range(2014, 2025):
        try:
            df = load_and_standardize_year(year, verbose=verbose)
            all_data.append(df)
        except FileNotFoundError as e:
            print(f"⚠️  Skipping {year}: {e}")
            continue

    # Combine all years
    combined = pd.concat(all_data, ignore_index=True)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Combined Dataset Summary")
        print(f"{'='*60}")
        print(f"Total rows: {len(combined):,}")
        print(f"Years: {sorted(combined['year'].unique())}")
        print(f"Columns: {list(combined.columns)}")
        print(f"\nPort nationalities: {sorted(combined['port_nationality'].dropna().unique())}")
        print(f"\nData types:")
        print(combined.dtypes)

    # Save to SQLite if path provided
    if output_path:
        db_path = Path(output_path)

        # Connect to database
        conn = sqlite3.connect(db_path)

        # Drop existing table
        conn.execute("DROP TABLE IF EXISTS landings")

        if verbose:
            print(f"\n{'='*60}")
            print(f"Writing to SQLite: {db_path}")
            print(f"{'='*60}")

        # Write to database
        combined.to_sql('landings', conn, index=False, if_exists='replace')

        # Create indexes
        if verbose:
            print("Creating indexes...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_year ON landings(year)",
            "CREATE INDEX IF NOT EXISTS idx_month ON landings(month)",
            "CREATE INDEX IF NOT EXISTS idx_port ON landings(port)",
            "CREATE INDEX IF NOT EXISTS idx_port_nationality ON landings(port_nationality)",
            "CREATE INDEX IF NOT EXISTS idx_vessel_nationality ON landings(vessel_nationality)",
            "CREATE INDEX IF NOT EXISTS idx_species_name ON landings(species_name)",
            "CREATE INDEX IF NOT EXISTS idx_species_code ON landings(species_code)",
            "CREATE INDEX IF NOT EXISTS idx_species_group ON landings(species_group)",
            "CREATE INDEX IF NOT EXISTS idx_gear_category ON landings(gear_category)",
            "CREATE INDEX IF NOT EXISTS idx_year_month ON landings(year, month)",
        ]

        for idx_sql in indexes:
            conn.execute(idx_sql)

        conn.commit()
        conn.close()

        if verbose:
            print(f"✓ Database saved: {db_path}")
            print(f"✓ Indexes created")

    return combined


if __name__ == "__main__":
    # Run standardization and save to database
    print("="*60)
    print("MMO Landing Data Standardization")
    print("="*60)

    output_db = "mmo_landings.db"

    df = standardize_all_years(output_path=output_db, verbose=True)

    print(f"\n{'='*60}")
    print("Sample of standardized data:")
    print(f"{'='*60}")
    print(df.head(10))

    print(f"\n✓ Complete! Database ready at: {output_db}")
