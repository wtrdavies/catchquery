"""
Quick test script to check what SQL the current system generates
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

SCHEMA_DESCRIPTION = """
TABLE: landings
Columns:
- year (INTEGER): Year of landing (e.g., 2024)
- month (INTEGER): Month of landing (1-12)
- port (TEXT): Name of port (e.g., 'Peterhead', 'Plymouth', 'Newlyn')
- port_nationality (TEXT): Region/country of port ('UK - Scotland', 'UK - England', 'UK - Wales', 'UK - Northern Ireland', 'Norway', 'Denmark', etc.)
- vessel_nationality (TEXT): Nationality of fishing vessel
- length_group (TEXT): '10m&Under' or 'Over10m'
- gear_category (TEXT): 'Trawl', 'Dredges', 'Traps', 'Nets', 'Lines', 'Seines'
- species_code (TEXT): Short code (e.g., 'MAC' for Mackerel)
- species_name (TEXT): Full name (e.g., 'Mackerel', 'Cod', 'Lobsters')
- species_group (TEXT): 'Pelagic', 'Demersal', 'Shellfish'
- live_weight_tonnes (REAL): Weight in tonnes
- landed_weight_tonnes (REAL): Weight landed in tonnes
- value_thousands (REAL): Value in £000s

Notes:
- "Scotland" means port_nationality = 'UK - Scotland'
- Value is in THOUSANDS of pounds
- For price per tonne: SUM(value_thousands) * 1000 / SUM(live_weight_tonnes)
"""

SYSTEM_PROMPT = f"""You convert natural language questions about UK fish landings into SQL queries.

{SCHEMA_DESCRIPTION}

Rules:
1. Return ONLY the SQL query, nothing else
2. Use valid SQLite syntax
3. Use ROUND() for numbers
4. Always include appropriate aggregations (SUM, AVG, COUNT)
5. Limit results to 20 rows unless asked otherwise
6. CRITICAL: Always include sufficient context columns so results are interpretable:
   - If aggregating by species, include species_name
   - If filtering by port, include port and port_nationality
   - If querying by time, include year and/or month
   - If involving vessel/gear, include length_group and gear_category
   - Include year in results unless the question is explicitly about a specific year
7. For monetary values:
   - Multiply value_thousands by 1000 in SELECT for clarity
   - Use clear aliases like 'total_value_pounds' not 'value'
8. Use meaningful column aliases (e.g., 'total_tonnes', 'avg_price_per_tonne_pounds')

If the question cannot be answered, return: SELECT 'Cannot answer this question with available data' as error
"""

# Test question
question = "list top five species landed in plymouth between 2020-2022"

print(f"Testing question: '{question}'")
print("=" * 80)

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "anthropic/claude-sonnet-4",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        "max_tokens": 512,
    }
)

data = response.json()
sql = data["choices"][0]["message"]["content"].strip()
sql = sql.replace("```sql", "").replace("```", "").strip()

print("\nGenerated SQL:")
print("-" * 80)
print(sql)
print("-" * 80)

print("\nExpected SQL:")
print("-" * 80)
expected = """SELECT species_name, ROUND(SUM(live_weight_tonnes), 2) as total_tonnes, ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE port = 'Plymouth' AND year BETWEEN 2020 AND 2022
GROUP BY species_name
ORDER BY total_tonnes DESC
LIMIT 5"""
print(expected)
print("-" * 80)

print("\n✓ Match!" if sql.strip() == expected.strip() else "\n✗ Does not match - this is the issue!")
