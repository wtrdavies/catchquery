"""
MMO Fish Landings Query Interface

A simple web interface for querying UK fish landing statistics.
Run with: streamlit run app.py
"""

import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import base64
from dotenv import load_dotenv

# Configuration
DB_PATH = "mmo_landings.db"

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    st.error("""
    **Missing API Key**

    Please set the OPENROUTER_API_KEY environment variable:

    ```bash
    export OPENROUTER_API_KEY="your-key-here"
    ```

    Then restart the application.
    """)
    st.stop()

SCHEMA_DESCRIPTION = """
TABLE: landings
Columns (use these exact names):
- year (INTEGER): Year of landing (2014-2024)
- month (INTEGER): Month of landing (1-12)
- port (TEXT): Port name (e.g., 'Peterhead', 'Plymouth', 'Newlyn')
- port_nationality (TEXT): Region/country of port:
    'Scotland', 'England', 'Wales', 'Northern Ireland',
    'Norway', 'Denmark', 'Netherlands', 'Ireland', 'France', etc.
- vessel_nationality (TEXT): Flag state of vessel (same values as port_nationality)
- length_group (TEXT): '10m&Under' or 'Over10m'
- gear_category (TEXT): 'Trawl', 'Dredges', 'Traps', 'Nets', 'Lines', 'Seines' (only available 2021-2024)
- species_code (TEXT): 3-letter code (e.g., 'MAC', 'COD', 'LBE') (only available 2021-2024)
- species_name (TEXT): Full name (e.g., 'Mackerel', 'Cod', 'Lobsters', 'Scallops')
- species_group (TEXT): 'Pelagic', 'Demersal', 'Shellfish'
- live_weight_tonnes (REAL): Catch weight in tonnes
- landed_weight_tonnes (REAL): Landed weight in tonnes
- value_thousands (REAL): Value in £000s (multiply by 1000 for actual pounds)

IMPORTANT:
- "Scotland" means port_nationality = 'Scotland' (not vessel_nationality)
- Value is stored in THOUSANDS - always multiply by 1000 in SELECT
- Price per tonne = SUM(value_thousands) * 1000 / SUM(live_weight_tonnes)
- Ignore any Title Case column variants - use only the snake_case names above
- Gear category and species_code only available from 2021 onwards (NULL for 2014-2020)
"""

SYSTEM_PROMPT = f"""You convert natural language questions about UK fish landings into SQL queries.

{SCHEMA_DESCRIPTION}

=== QUERY PLANNING ===

Before writing SQL, mentally identify:
1. MEASURE: What quantity is being asked for? (tonnes, value, count, price)
2. FILTERS: What conditions limit the data? (year, port, species, etc.)
3. GROUPING: How should results be segmented? (by species, by port, by year, etc.)
4. ORDERING: How should results be sorted? (most to least, chronologically, etc.)
5. LIMIT: How many results? (top 5, top 10, or all)

=== CRITICAL RULES ===

RULE 1 - TEMPORAL HANDLING (IMPORTANT):
The distinction between FILTERING by time and GROUPING by time is crucial.

• DATE RANGE queries ("between 2020-2022", "from 2015 to 2023", "over the last 5 years"):
  - Use WHERE year BETWEEN X AND Y
  - Do NOT add year to GROUP BY (this would split the aggregation incorrectly)
  - Do NOT add year to SELECT
  - The user wants TOTALS across the range, not yearly breakdowns

• SINGLE YEAR queries ("in 2024", "for 2023"):
  - Use WHERE year = XXXX
  - Do NOT add year to SELECT (it's redundant - every row is that year)

• TREND/BREAKDOWN queries ("by year", "year on year", "trend over time", "annually"):
  - Include year in SELECT
  - Include year in GROUP BY
  - ORDER BY year

RULE 2 - GROUP BY LOGIC:
Only include columns in GROUP BY that the user wants to SEGMENT results by.
- "top species" → GROUP BY species_name only
- "top species by port" → GROUP BY species_name, port
- "landings by year and species" → GROUP BY year, species_name

RULE 3 - OUTPUT FORMAT:
- Return ONLY the SQL query, no explanation
- Use valid SQLite syntax
- Use ROUND() for all numerical outputs
- Use meaningful aliases: total_tonnes, total_value_pounds, avg_price_per_tonne

RULE 4 - MONETARY VALUES:
- Always multiply value_thousands by 1000: ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
- For price per tonne: ROUND(SUM(value_thousands) * 1000 / SUM(live_weight_tonnes), 2)

RULE 5 - LIMITS:
- If user says "top N" or "N largest", use LIMIT N
- If no limit specified, default to LIMIT 20
- Always ORDER BY the relevant measure DESC for "top" queries

RULE 6 - CONTEXT COLUMNS:
Include columns that make results interpretable:
- Aggregating by species? Include species_name
- Filtering by port? Include port in SELECT only if grouping by it
- Grouping by port? Include port and port_nationality

RULE 7 - TOP N PER GROUP (CRITICAL):
When user asks to "compare top N" across multiple groups, use window functions to rank WITHIN each group.

Pattern: "compare top 5 species at Plymouth and Brixham" = top 5 per port, not top 5 overall

WRONG (gives top N overall, not per group):
```sql
SELECT port, species_name, SUM(value) as total
FROM landings
WHERE port IN ('Plymouth', 'Brixham')
GROUP BY port, species_name
ORDER BY port, total DESC
LIMIT 10  -- This will give all from first port alphabetically!
```

CORRECT (gives top N per group using window function):
```sql
WITH ranked AS (
  SELECT port, species_name,
         ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds,
         ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
         ROW_NUMBER() OVER (PARTITION BY port ORDER BY SUM(value_thousands) DESC) as rank
  FROM landings
  WHERE port IN ('Plymouth', 'Brixham')
    AND year BETWEEN 2017 AND 2023
  GROUP BY port, species_name
)
SELECT port, species_name, total_value_pounds, total_tonnes
FROM ranked
WHERE rank <= 5
ORDER BY port, rank
```

Keywords that indicate TOP N PER GROUP:
- "compare top N [thing] at/between [multiple groups]"
- "top N for each [group]"
- "show me top N [thing] by [group]"

=== EXAMPLES ===

Q: "top 5 species landed in Plymouth between 2020-2022"
```sql
SELECT species_name,
       ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
       ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE port = 'Plymouth'
  AND year BETWEEN 2020 AND 2022
GROUP BY species_name
ORDER BY total_tonnes DESC
LIMIT 5
```

Q: "yearly mackerel landings in Scotland from 2018 to 2023"
```sql
SELECT year,
       ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
       ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE species_name = 'Mackerel'
  AND port_nationality = 'Scotland'
  AND year BETWEEN 2018 AND 2023
GROUP BY year
ORDER BY year
```

Q: "which port landed the most cod in 2024?"
```sql
SELECT port, port_nationality,
       ROUND(SUM(live_weight_tonnes), 2) as total_tonnes
FROM landings
WHERE species_name = 'Cod'
  AND year = 2024
GROUP BY port, port_nationality
ORDER BY total_tonnes DESC
LIMIT 1
```

Q: "compare shellfish landings between England and Scotland in 2023"
```sql
SELECT port_nationality,
       ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
       ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE species_group = 'Shellfish'
  AND year = 2023
  AND port_nationality IN ('England', 'Scotland')
GROUP BY port_nationality
ORDER BY total_tonnes DESC
```

Q: "average price per tonne of lobster by year"
```sql
SELECT year,
       ROUND(SUM(value_thousands) * 1000 / SUM(live_weight_tonnes), 2) as avg_price_per_tonne
FROM landings
WHERE species_name = 'Lobsters'
  AND live_weight_tonnes > 0
GROUP BY year
ORDER BY year
```

Q: "total value of all landings in Newlyn"
```sql
SELECT ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE port = 'Newlyn'
```

Q: "monthly breakdown of herring landings in 2024"
```sql
SELECT month,
       ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
       ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE species_name = 'Herring'
  AND year = 2024
GROUP BY month
ORDER BY month
```

Q: "top 10 ports for scallops across all years"
```sql
SELECT port, port_nationality,
       ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
       ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE species_name = 'Scallops'
GROUP BY port, port_nationality
ORDER BY total_tonnes DESC
LIMIT 10
```

Q: "compare the top 5 species by value at Plymouth and Brixham between 2017-2023"
```sql
WITH ranked AS (
  SELECT port,
         species_name,
         ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds,
         ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
         ROW_NUMBER() OVER (PARTITION BY port ORDER BY SUM(value_thousands) DESC) as rank
  FROM landings
  WHERE port IN ('Plymouth', 'Brixham')
    AND year BETWEEN 2017 AND 2023
  GROUP BY port, species_name
)
SELECT port, species_name, total_value_pounds, total_tonnes
FROM ranked
WHERE rank <= 5
ORDER BY port, rank
```

=== ERROR HANDLING ===

If the question cannot be answered with available data, return:
SELECT 'Cannot answer this question with available data' as error

Common issues to watch for:
- Species name might need fuzzy matching (e.g., 'crab' could be 'Crabs (C.P.Mixed)', 'Crabs - Loss', etc.)
- For partial matches, suggest: WHERE species_name LIKE '%Crab%'
"""


import requests

def get_sql_from_llm(question: str):
    """Get SQL query from Claude via OpenRouter"""
    try:
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
        response.raise_for_status()
        data = response.json()
        sql = data["choices"][0]["message"]["content"].strip()
        # Remove markdown code fences if present
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Invalid API key. Please check OPENROUTER_API_KEY environment variable.")
        elif e.response.status_code == 429:
            st.error("Rate limit exceeded. Please try again in a moment.")
        else:
            st.error(f"API error ({e.response.status_code}): {e}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

def run_query(sql: str, db_path: str):
    """Execute SQL and return DataFrame"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)

def generate_table_description(question: str, sql: str, df: pd.DataFrame) -> str:
    """Generate natural language description of query results"""
    try:
        sample_data = df.head(5).to_dict('records')

        description_prompt = f"""Given this user question: "{question}"

And this SQL query: {sql}

Sample results (first 5 rows): {sample_data}
Total rows: {len(df)}

Provide a clear, 1-2 sentence description explaining what this table shows and key findings.
Be conversational. Focus on interpreting data for marine economics consultants."""

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-sonnet-4",
                "messages": [{"role": "user", "content": description_prompt}],
                "max_tokens": 256,
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"Table showing {len(df)} results for your query."


def analyze_empty_results(sql: str, question: str, db_path: str) -> dict:
    """Analyze why query returned empty results and suggest alternatives"""
    try:
        conn = sqlite3.connect(db_path)

        # Extract filters from SQL using simple parsing
        sql_upper = sql.upper()
        filters = {
            'port': None,
            'species': None,
            'year_range': None,
            'port_nationality': None
        }

        # Parse port filter
        if "PORT = '" in sql_upper:
            start = sql.upper().index("PORT = '") + 8
            end = sql.index("'", start)
            filters['port'] = sql[start:end]

        # Parse species filter
        if "SPECIES_NAME = '" in sql_upper:
            start = sql.upper().index("SPECIES_NAME = '") + 16
            end = sql.index("'", start)
            filters['species'] = sql[start:end]

        # Parse year range
        if "YEAR BETWEEN" in sql_upper:
            between_idx = sql_upper.index("YEAR BETWEEN") + 13
            and_idx = sql_upper.index("AND", between_idx)
            year_start = sql[between_idx:and_idx].strip()
            year_end_part = sql[and_idx+3:].split()[0].strip()
            filters['year_range'] = (int(year_start), int(year_end_part))
        elif "YEAR =" in sql_upper:
            year_idx = sql_upper.index("YEAR =") + 7
            year_val = sql[year_idx:].split()[0].strip()
            filters['year_range'] = (int(year_val), int(year_val))

        suggestions = []

        # Check what years are available for the specified port
        if filters['port']:
            year_query = f"SELECT MIN(year) as min_year, MAX(year) as max_year, COUNT(DISTINCT year) as year_count FROM landings WHERE port = ?"
            cursor = conn.execute(year_query, (filters['port'],))
            result = cursor.fetchone()

            if result and result[2] > 0:
                min_year, max_year, year_count = result
                suggestions.append(f"**{filters['port']}** has data available from **{min_year} to {max_year}** ({year_count} years)")

                if filters['year_range']:
                    req_start, req_end = filters['year_range']
                    suggestions.append(f"You requested {req_start}-{req_end}, but try: **{min_year}-{max_year}**")
            else:
                # Port has no data at all
                suggestions.append(f"**{filters['port']}** doesn't exist in the database or has no recorded landings")

                # Find similar port names
                similar_query = "SELECT DISTINCT port FROM landings WHERE port LIKE ? LIMIT 5"
                cursor = conn.execute(similar_query, (f"%{filters['port'][:3]}%",))
                similar_ports = [row[0] for row in cursor.fetchall()]
                if similar_ports:
                    suggestions.append(f"Did you mean: {', '.join(similar_ports[:3])}?")

        # Check what species are available for the specified filters
        if filters['species'] and filters['port']:
            species_query = "SELECT COUNT(*) FROM landings WHERE port = ? AND species_name = ?"
            cursor = conn.execute(species_query, (filters['port'], filters['species']))
            count = cursor.fetchone()[0]

            if count == 0:
                # Check what species ARE available at this port
                available_query = """
                    SELECT species_name, SUM(live_weight_tonnes) as total_tonnes
                    FROM landings
                    WHERE port = ?
                    GROUP BY species_name
                    ORDER BY total_tonnes DESC
                    LIMIT 5
                """
                cursor = conn.execute(available_query, (filters['port'],))
                top_species = [row[0] for row in cursor.fetchall()]
                if top_species:
                    suggestions.append(f"Top species at {filters['port']}: {', '.join(top_species)}")

        # Check what years exist in database overall
        if filters['year_range'] and not filters['port']:
            overall_years_query = "SELECT MIN(year), MAX(year) FROM landings"
            cursor = conn.execute(overall_years_query)
            min_year, max_year = cursor.fetchone()
            suggestions.append(f"Database contains data from **{min_year} to {max_year}**")

        conn.close()

        return {
            'filters': filters,
            'suggestions': suggestions
        }

    except Exception as e:
        return {
            'filters': {},
            'suggestions': [f"Unable to analyze query: {str(e)}"]
        }


# Streamlit UI
st.set_page_config(page_title="CatchQuery UK", layout="wide")

# Add background image with opacity
def get_base64_image(image_path):
    """Convert image to base64 for CSS embedding"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Get base64 of background image
bg_image = get_base64_image("background.png")

st.markdown(f"""
<style>
    /* Main app background with faded maritime image */
    .stApp {{
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)),
                          url("data:image/png;base64,{bg_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    /* Ensure content is readable over background */
    .stApp > header {{
        background-color: rgba(255, 255, 255, 0.95);
    }}
</style>
""", unsafe_allow_html=True)

st.title("CatchQuery UK")
st.markdown("Use natural language to explore UK fisheries data")

# Introductory paragraph
st.markdown("""
This tool provides access to UK fish landing statistics from the Marine Management Organisation (MMO),
covering the period from 2014 to 2024. The dataset contains detailed records of commercial fish landings
at UK ports, including species caught, landing locations, vessel nationalities, fishing gear types,
catch weights and monetary values. You can query by specific ports, species, time periods, regional
comparisons or vessel characteristics to explore trends and patterns in UK fisheries.
""")

st.markdown("")  # Add spacing

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Hide Streamlit's running indicator */
    .stSpinner {
        display: none !important;
    }
    div[data-testid="stStatusWidget"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSpinner"] {
        display: none !important;
    }

    /* Professional typography */
    * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }

    /* Title styling */
    h1 {
        color: #2C5F7C !important;
        font-weight: 500 !important;
        letter-spacing: -0.3px !important;
        font-size: 2.2rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Subtitle and body text */
    p, div {
        line-height: 1.6 !important;
    }

    /* Button styling - more subtle */
    div.stButton > button {
        background-color: #F8FBFC;
        color: #2C5F7C;
        border: 1px solid #C5D9E3;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div.stButton > button:hover {
        background-color: #EBF4F8;
        border-color: #2C5F7C;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Primary button styling */
    div.stButton > button[kind="primary"] {
        background-color: #2C5F7C;
        color: white;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #234B61;
    }
</style>
""", unsafe_allow_html=True)

# Main interface with form for Enter key support
with st.form(key="query_form", clear_on_submit=False):
    question = st.text_input(
        "Your question:",
        placeholder="e.g., What are the top 5 ports for shellfish landings?",
    )

    col1, col2 = st.columns([6, 1])
    with col1:
        run_button = st.form_submit_button("Query", type="primary", use_container_width=False)
    with col2:
        reset_button = st.form_submit_button("Reset", use_container_width=True)

# Handle reset
if reset_button:
    st.rerun()

if run_button and question and not reset_button:
    start_time = time.time()
    status_placeholder = st.empty()
    status_placeholder.info("Processing your query...")

    try:
        sql = get_sql_from_llm(question)

        df, error = run_query(sql, DB_PATH)
        elapsed = time.time() - start_time
        status_placeholder.empty()

        if error:
            st.error(f"Query error: {error}")
        elif df is not None:
            # Check if results are empty (0 rows) or contain only NULL aggregations (1 row with all NULLs)
            is_empty = len(df) == 0
            is_null_aggregation = (len(df) == 1 and df.select_dtypes(include=['number']).isna().all().all())

            if is_empty or is_null_aggregation:
                st.warning("No results found for your query.")

                # Analyze why and provide suggestions
                analysis = analyze_empty_results(sql, question, DB_PATH)

                if analysis['suggestions']:
                    st.info("**Suggestions:**")
                    for suggestion in analysis['suggestions']:
                        st.markdown(f"- {suggestion}")

                # Still show the SQL
                with st.expander("View Generated SQL", expanded=True):
                    st.code(sql, language="sql")

                st.caption(f"Query executed in {elapsed:.2f} seconds")
            else:
                # Normal results display
                st.subheader("Results")

                # Transform column names to Title Case
                def format_column_name(col_name: str) -> str:
                    """Transform snake_case to Title Case"""
                    special_cases = {
                        'uk': 'UK',
                        'tonnes': 'Tonnes',
                        'thousands': '(£000s)',
                    }

                    words = col_name.replace('_', ' ').split()
                    formatted_words = []

                    for word in words:
                        if word.lower() in special_cases:
                            formatted_words.append(special_cases[word.lower()])
                        else:
                            formatted_words.append(word.capitalize())

                    return ' '.join(formatted_words)

                # Transform column names
                df.columns = [format_column_name(col) for col in df.columns]

                # Format numeric columns
                for col in df.columns:
                    if df[col].dtype in ['float64', 'float32']:
                        if 'value' in col.lower() or 'pound' in col.lower():
                            df[col] = df[col].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "")
                        else:
                            df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")

                # Apply Pandas Styler for enhanced table aesthetics
                styled_df = df.style.set_properties(**{
                    'background-color': '#F0F8FF',
                    'color': '#1A3A52',
                    'border-color': '#1E5A8E',
                    'padding': '10px'
                }).set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', '#1E5A8E'),
                        ('color', 'white'),
                        ('font-weight', 'bold'),
                        ('padding', '12px')
                    ]},
                    {'selector': 'tr:nth-child(even)', 'props': [
                        ('background-color', '#F0F8FF')
                    ]},
                    {'selector': 'tr:nth-child(odd)', 'props': [
                        ('background-color', 'white')
                    ]},
                    {'selector': 'tr:hover', 'props': [
                        ('background-color', '#D0E8F7')
                    ]},
                    {'selector': 'table', 'props': [
                        ('border-radius', '8px'),
                        ('overflow', 'hidden')
                    ]}
                ])

                st.dataframe(styled_df, use_container_width=True, hide_index=True)

                # Generate and display description
                with st.spinner("Generating description..."):
                    description = generate_table_description(question, sql, df)
                st.markdown(f"**About this data**: {description}")

                st.caption(f"Query executed in {elapsed:.2f} seconds")

                # SQL display in collapsible expander (after results)
                with st.expander("View Generated SQL", expanded=False):
                    st.code(sql, language="sql")

                # Option to download
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "query_results.csv",
                    "text/csv",
                )

    except Exception as e:
        st.error(f"Error: {e}")

# Footer with two columns
st.markdown("---")

footer_col1, footer_col2 = st.columns([2, 1])

with footer_col1:
    st.markdown(
        "Data source: [Marine Management Organisation](https://www.gov.uk/government/collections/monthly-uk-sea-fisheries-statistics)"
    )

with footer_col2:
    st.markdown("**Created by**")
    try:
        st.image("AdaptMEL_logo.png", width=120)
    except Exception:
        st.markdown("*AdaptMEL*")

# Disclaimers
st.markdown("")  # Spacing
st.markdown("""
<p style="font-size: 0.85rem; color: #6c757d; text-align: center; margin-top: 2rem;">
This tool uses AI to generate database queries, which may occasionally produce inaccurate results.
Please verify important findings against the source data.
</p>
""", unsafe_allow_html=True)

st.markdown("""
<p style="font-size: 0.8rem; color: #6c757d; text-align: center; margin-top: 0.5rem;">
Contains public sector information licensed under the Open Government Licence v3.0.
<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
style="color: #6c757d; text-decoration: underline;">View licence</a>
</p>
""", unsafe_allow_html=True)
