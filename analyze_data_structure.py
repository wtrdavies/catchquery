"""
Analyze MMO landing data structure across all years (2014-2024)
to identify column variations and terminology inconsistencies.
"""

import pandas as pd
from pathlib import Path

def analyze_year(year: int) -> dict:
    """Analyze structure and content of a single year's data."""
    file_path = Path(f"data/{year}.csv")

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return None

    print(f"\n{'='*60}")
    print(f"Analyzing {year}")
    print(f"{'='*60}")

    # Read CSV
    df = pd.read_csv(file_path)

    print(f"\nRows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"\nColumn names:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")

    # Analyze key fields
    results = {
        'year': year,
        'rows': len(df),
        'columns': list(df.columns),
    }

    # Check for nationality-related columns
    print(f"\n--- Port Nationality ---")
    nationality_col = None
    for col in df.columns:
        if 'nationality' in col.lower() and 'port' in col.lower():
            nationality_col = col
            break

    if nationality_col:
        unique_vals = df[nationality_col].dropna().unique()
        print(f"Column: {nationality_col}")
        print(f"Unique values ({len(unique_vals)}):")
        for val in sorted(unique_vals)[:15]:
            count = len(df[df[nationality_col] == val])
            print(f"  - {val} ({count:,} rows)")
        if len(unique_vals) > 15:
            print(f"  ... and {len(unique_vals) - 15} more")
        results['nationality_column'] = nationality_col
        results['nationalities'] = sorted(unique_vals)
    else:
        print("⚠️ No port nationality column found")

    # Check for species columns
    print(f"\n--- Species ---")
    species_col = None
    for col in df.columns:
        if col.lower() == 'species' or 'species name' in col.lower():
            species_col = col
            break

    if species_col:
        unique_species = df[species_col].dropna().unique()
        print(f"Column: {species_col}")
        print(f"Unique species: {len(unique_species)}")
        print(f"Sample (first 10):")
        for species in sorted(unique_species)[:10]:
            print(f"  - {species}")
        results['species_column'] = species_col
        results['species_count'] = len(unique_species)
    else:
        print("⚠️ No species column found")

    # Check for vessel nationality
    print(f"\n--- Vessel Nationality ---")
    vessel_nat_col = None
    for col in df.columns:
        if 'vessel' in col.lower() and 'nationality' in col.lower():
            vessel_nat_col = col
            break

    if vessel_nat_col:
        unique_vals = df[vessel_nat_col].dropna().unique()
        print(f"Column: {vessel_nat_col}")
        print(f"Unique values: {len(unique_vals)}")
        print(f"Sample:")
        for val in sorted(unique_vals)[:10]:
            print(f"  - {val}")
        results['vessel_nationality_column'] = vessel_nat_col
    else:
        print("⚠️ No vessel nationality column found")

    # Check for gear/method columns
    print(f"\n--- Gear/Method ---")
    gear_col = None
    for col in df.columns:
        if 'gear' in col.lower() or 'method' in col.lower():
            gear_col = col
            break

    if gear_col:
        unique_vals = df[gear_col].dropna().unique()
        print(f"Column: {gear_col}")
        print(f"Unique values: {len(unique_vals)}")
        for val in sorted(unique_vals):
            print(f"  - {val}")
        results['gear_column'] = gear_col
    else:
        print("⚠️ No gear column found")

    return results

def main():
    """Analyze all years and summarize findings."""
    print("MMO Landing Data Structure Analysis")
    print("="*60)

    all_results = []

    # Analyze each year
    for year in range(2014, 2025):
        result = analyze_year(year)
        if result:
            all_results.append(result)

    # Summary comparison
    print(f"\n\n{'='*60}")
    print("SUMMARY: Column Name Consistency")
    print(f"{'='*60}")

    # Check if column names are consistent
    if all_results:
        first_cols = set(all_results[0]['columns'])
        inconsistent = False

        for result in all_results[1:]:
            current_cols = set(result['columns'])
            if current_cols != first_cols:
                inconsistent = True
                print(f"\n⚠️ {result['year']} has different columns:")
                added = current_cols - first_cols
                removed = first_cols - current_cols
                if added:
                    print(f"  Added: {added}")
                if removed:
                    print(f"  Removed: {removed}")

        if not inconsistent:
            print("\n✓ All years have identical column structure")

    # Check nationality format consistency
    print(f"\n\n{'='*60}")
    print("SUMMARY: Nationality Format Patterns")
    print(f"{'='*60}")

    # Collect all unique nationality values across years
    all_nationalities = set()
    for result in all_results:
        if 'nationalities' in result:
            all_nationalities.update(result['nationalities'])

    if all_nationalities:
        print("\nAll unique nationality values across all years:")
        for nat in sorted(all_nationalities):
            print(f"  - {nat}")

        # Identify patterns
        print("\nPatterns detected:")
        uk_prefix = [n for n in all_nationalities if n.startswith('UK -')]
        no_prefix = [n for n in all_nationalities if not n.startswith('UK -') and 'England' in n or 'Scotland' in n or 'Wales' in n or 'Ireland' in n]

        if uk_prefix:
            print(f"  - {len(uk_prefix)} values use 'UK -' prefix")
        if no_prefix:
            print(f"  - {len(no_prefix)} values without 'UK -' prefix")

if __name__ == "__main__":
    main()
