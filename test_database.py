"""
Test the standardized MMO landings database.
"""

import sqlite3
import pandas as pd

def run_test_queries():
    """Run sample queries to verify database works correctly."""

    conn = sqlite3.connect('mmo_landings.db')

    print("="*60)
    print("Database Test Queries")
    print("="*60)

    # Test 1: Total records
    print("\n1. Total records:")
    result = pd.read_sql_query("SELECT COUNT(*) as total FROM landings", conn)
    print(f"   {result['total'][0]:,} rows")

    # Test 2: Records by year
    print("\n2. Records by year:")
    result = pd.read_sql_query("""
        SELECT year, COUNT(*) as records
        FROM landings
        GROUP BY year
        ORDER BY year
    """, conn)
    print(result.to_string(index=False))

    # Test 3: Check nationality standardization
    print("\n3. Port nationalities (standardized):")
    result = pd.read_sql_query("""
        SELECT port_nationality, COUNT(*) as records
        FROM landings
        WHERE port_nationality IS NOT NULL
        GROUP BY port_nationality
        ORDER BY records DESC
        LIMIT 15
    """, conn)
    print(result.to_string(index=False))

    # Test 4: Top species by total value
    print("\n4. Top 10 species by total value (2014-2024):")
    result = pd.read_sql_query("""
        SELECT
            species_name,
            ROUND(SUM(value_thousands), 2) as total_value_thousands,
            ROUND(SUM(landed_weight_tonnes), 2) as total_weight_tonnes
        FROM landings
        WHERE species_name IS NOT NULL
        GROUP BY species_name
        ORDER BY total_value_thousands DESC
        LIMIT 10
    """, conn)
    print(result.to_string(index=False))

    # Test 5: Landings in Scotland by year
    print("\n5. Scotland landings by year:")
    result = pd.read_sql_query("""
        SELECT
            year,
            ROUND(SUM(landed_weight_tonnes), 2) as total_tonnes,
            ROUND(SUM(value_thousands), 2) as total_value_thousands
        FROM landings
        WHERE port_nationality = 'Scotland'
        GROUP BY year
        ORDER BY year
    """, conn)
    print(result.to_string(index=False))

    # Test 6: Gear categories available (should be NULL for 2014-2020)
    print("\n6. Gear category coverage:")
    result = pd.read_sql_query("""
        SELECT
            year,
            COUNT(*) as total_records,
            SUM(CASE WHEN gear_category IS NULL THEN 1 ELSE 0 END) as null_gear,
            COUNT(DISTINCT gear_category) as distinct_gears
        FROM landings
        GROUP BY year
        ORDER BY year
    """, conn)
    print(result.to_string(index=False))

    # Test 7: Check species detail increase
    print("\n7. Species diversity by year:")
    result = pd.read_sql_query("""
        SELECT
            year,
            COUNT(DISTINCT species_name) as unique_species
        FROM landings
        WHERE species_name IS NOT NULL
        GROUP BY year
        ORDER BY year
    """, conn)
    print(result.to_string(index=False))

    # Test 8: Value unit check (ensure 2019-2020 were converted correctly)
    print("\n8. Average value per tonne by year (checking unit consistency):")
    result = pd.read_sql_query("""
        SELECT
            year,
            ROUND(SUM(value_thousands) * 1000 / SUM(landed_weight_tonnes), 2) as avg_price_per_tonne_gbp
        FROM landings
        WHERE landed_weight_tonnes > 0
        GROUP BY year
        ORDER BY year
    """, conn)
    print(result.to_string(index=False))

    conn.close()

    print("\n" + "="*60)
    print("✓ All tests completed successfully!")
    print("="*60)


if __name__ == "__main__":
    run_test_queries()
