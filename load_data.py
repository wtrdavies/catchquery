"""
Data Loader for MMO Fish Landing Statistics

Processes ODS/Excel files from the MMO and loads them into SQLite.

Usage:
    python load_data.py [data_folder] [output_db]
    
    data_folder: Folder containing ODS/XLSX files (default: ./data)
    output_db: Output database path (default: ./mmo_landings.db)
"""

import sys
import os
import sqlite3
import pandas as pd
from pathlib import Path


def load_mmo_file(filepath: Path):
    """Load a single MMO data file (ODS or XLSX)"""
    
    print(f"  Loading: {filepath.name}")
    
    try:
        # Determine engine based on file type
        if filepath.suffix.lower() == '.ods':
            engine = 'odf'
        elif filepath.suffix.lower() in ['.xlsx', '.xls']:
            engine = 'openpyxl'
        else:
            print(f"    Skipping unsupported file type: {filepath.suffix}")
            return None
        
        # Load the file and check for 'Data' sheet
        xlsx = pd.ExcelFile(filepath, engine=engine)
        
        if 'Data' not in xlsx.sheet_names:
            print(f"    No 'Data' sheet found. Available sheets: {xlsx.sheet_names}")
            return None
        
        df = pd.read_excel(xlsx, sheet_name='Data')
        print(f"    Loaded {len(df):,} rows")
        
        return df
        
    except Exception as e:
        print(f"    Error loading file: {e}")
        return None


def standardise_columns(df: pd.DataFrame):
    """Standardise column names to match our schema"""
    
    # Expected columns from MMO files (may vary slightly between years)
    column_mapping = {
        'Year': 'year',
        'Month': 'month',
        'Port of landing': 'port',
        'Port Nationality': 'port_nationality',
        'Vessel nationality': 'vessel_nationality',
        'Length Group': 'length_group',
        'Gear category': 'gear_category',
        'Species code': 'species_code',
        'Species name': 'species_name',
        'Species group': 'species_group',
        'Live Weight (tonnes)': 'live_weight_tonnes',
        'Landed Weight (tonnes)': 'landed_weight_tonnes',
        'Value (£000s)': 'value_thousands',
        # Alternative column names that might appear
        'Value (£)': 'value_thousands',  # Will need conversion
        'Live Weight': 'live_weight_tonnes',
        'Landed Weight': 'landed_weight_tonnes',
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Ensure we have the required columns
    required = ['year', 'month', 'port', 'species_name', 'live_weight_tonnes', 'value_thousands']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"    Warning: Missing columns: {missing}")
    
    return df


def create_database(db_path: str, dataframes: list[pd.DataFrame]):
    """Create SQLite database from list of DataFrames"""
    
    if not dataframes:
        print("No data to load!")
        return
    
    # Combine all dataframes
    print("\nCombining datasets...")
    combined = pd.concat(dataframes, ignore_index=True)
    print(f"Total rows: {len(combined):,}")
    
    # Remove any complete duplicates
    before = len(combined)
    combined = combined.drop_duplicates()
    after = len(combined)
    if before != after:
        print(f"Removed {before - after:,} duplicate rows")
    
    # Create database
    print(f"\nCreating database: {db_path}")
    conn = sqlite3.connect(db_path)
    
    # Load data
    combined.to_sql('landings', conn, if_exists='replace', index=False)
    
    # Create indexes for common queries
    print("Creating indexes...")
    indexes = [
        'CREATE INDEX idx_port ON landings(port)',
        'CREATE INDEX idx_species ON landings(species_name)',
        'CREATE INDEX idx_year_month ON landings(year, month)',
        'CREATE INDEX idx_port_nationality ON landings(port_nationality)',
        'CREATE INDEX idx_species_group ON landings(species_group)',
    ]
    
    for idx_sql in indexes:
        try:
            conn.execute(idx_sql)
        except sqlite3.OperationalError:
            pass  # Index might already exist
    
    conn.commit()
    
    # Print summary
    print("\n" + "=" * 50)
    print("DATABASE SUMMARY")
    print("=" * 50)
    
    summary_queries = [
        ("Total records", "SELECT COUNT(*) FROM landings"),
        ("Year range", "SELECT MIN(year) || ' - ' || MAX(year) FROM landings"),
        ("Unique ports", "SELECT COUNT(DISTINCT port) FROM landings"),
        ("Unique species", "SELECT COUNT(DISTINCT species_name) FROM landings"),
        ("Total value (£m)", "SELECT ROUND(SUM(value_thousands)/1000, 1) FROM landings"),
        ("Total weight (kt)", "SELECT ROUND(SUM(live_weight_tonnes)/1000, 1) FROM landings"),
    ]
    
    for label, query in summary_queries:
        result = conn.execute(query).fetchone()[0]
        print(f"{label}: {result}")
    
    conn.close()
    print(f"\nDatabase saved to: {db_path}")


def main():
    # Parse arguments
    data_folder = sys.argv[1] if len(sys.argv) > 1 else "./data"
    output_db = sys.argv[2] if len(sys.argv) > 2 else "./mmo_landings.db"
    
    data_path = Path(data_folder)
    
    if not data_path.exists():
        print(f"Data folder not found: {data_folder}")
        print("Please create a 'data' folder and add MMO ODS/XLSX files.")
        sys.exit(1)
    
    # Find all data files
    files = list(data_path.glob("*.ods")) + list(data_path.glob("*.xlsx"))
    
    if not files:
        print(f"No ODS or XLSX files found in {data_folder}")
        sys.exit(1)
    
    print(f"Found {len(files)} data file(s)")
    print("=" * 50)
    
    # Load each file
    dataframes = []
    for filepath in sorted(files):
        df = load_mmo_file(filepath)
        if df is not None:
            df = standardise_columns(df)
            dataframes.append(df)
    
    # Create database
    create_database(output_db, dataframes)


if __name__ == "__main__":
    main()
