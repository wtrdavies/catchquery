# Natural Language to SQL Improvement - Consultation Document

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Context](#project-context)
3. [Database Schema](#database-schema)
4. [Current Implementation](#current-implementation)
5. [Example Queries](#example-queries)
6. [Specific Help Needed](#specific-help-needed)
7. [Full Code Listings](#full-code-listings)

---

## Executive Summary

**Tool Name:** CatchQuery UK - MMO Fish Landings Query Tool

**Purpose:** A natural language interface for querying UK fish landing statistics from the Marine Management Organisation (MMO). Users ask questions in plain English and receive SQL-generated results.

**Target Users:** Marine economics consultants and researchers who need to quickly interrogate MMO landing data without writing SQL themselves.

**Current Problem:** The natural language to SQL conversion works well for simple queries but struggles with more complex requests involving:
- Multi-year date ranges with multiple filters
- Temporal comparisons across years
- Complex aggregations with nested conditions
- Queries requiring sophisticated GROUP BY or WHERE clauses

**Example Failing Query:**
"list top five species landed in plymouth between 2020-2022"

This query should work (the data exists and a simple SQL query returns results), but the current system prompt doesn't generate the correct SQL consistently.

**Goal of This Consultation:**
Get expert guidance on improving the SYSTEM_PROMPT and overall approach to handle complex natural language queries more robustly.

---

## Project Context

### Overview

A Streamlit-based web application that converts natural language questions about UK fish landings into SQL queries, executes them against a SQLite database, and displays results in a user-friendly format.

### Tech Stack

- **Python 3.9+**
- **SQLite** - Local database with MMO landing records
- **Streamlit** - Web interface
- **OpenRouter API** - Routes to Claude Sonnet 4 for NL-to-SQL conversion
- **Pandas** - Data manipulation and display

### Data Coverage

- **Date Range:** 2008-2024 (17 years)
- **Total Records:** ~1,250,000 rows
- **Ports:** ~509 different UK and international ports
- **Species:** ~174 different species
- **Data Granularity:** Monthly aggregations by port, species, gear type, vessel size

### Use Cases

Users typically ask questions like:
- "Which port landed the most mackerel in 2024?"
- "What are the top 5 species by value?"
- "How much mackerel was landed in Scotland?"
- "Compare shellfish landings between England and Scotland"
- "Average price per tonne of lobster?"
- "Show me landings in Plymouth by species"

### Key Challenge

While simple queries work well, the system struggles with queries that combine:
- Temporal ranges (BETWEEN years)
- Location filters (specific ports)
- Aggregations (TOP N)
- Multiple grouping dimensions

---

## Database Schema

### Table: `landings`

The database contains a single table with the following structure:

```sql
CREATE TABLE "landings" (
  "year" INTEGER,
  "month" INTEGER,
  "port" TEXT,
  "port_nationality" TEXT,
  "vessel_nationality" TEXT,
  "length_group" TEXT,
  "gear_category" TEXT,
  "species_code" TEXT,
  "species_name" TEXT,
  "species_group" TEXT,
  "live_weight_tonnes" REAL,
  "landed_weight_tonnes" REAL,
  "value_thousands" REAL,
  "Port of Landing" TEXT,
  "Vessel Nationality" TEXT,
  "Gear Category" TEXT,
  "Species Code" TEXT,
  "Species Name" TEXT,
  "Species Group" TEXT,
  "Value(£)" REAL
)
```

**Note:** The schema has some inconsistency with duplicate columns in different naming conventions (snake_case vs Title Case). This is due to data loading variations across years. The primary columns to use are the snake_case versions.

### Column Descriptions

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `year` | INTEGER | Year of landing | 2008-2024 |
| `month` | INTEGER | Month of landing | 1-12 |
| `port` | TEXT | Port name | 'Peterhead', 'Plymouth', 'Newlyn' |
| `port_nationality` | TEXT | Region/country of port | 'UK - Scotland', 'UK - England', 'UK - Wales', 'UK - Northern Ireland', 'Norway', 'Denmark' |
| `vessel_nationality` | TEXT | Flag state of vessel | Same values as port_nationality |
| `length_group` | TEXT | Vessel size category | '10m&Under', 'Over10m' |
| `gear_category` | TEXT | Fishing method | 'Trawl', 'Dredges', 'Traps', 'Nets', 'Lines', 'Seines' |
| `species_code` | TEXT | 3-letter species code | 'MAC' (Mackerel), 'COD', 'LBE' (Lobster) |
| `species_name` | TEXT | Full species name | 'Mackerel', 'Cod', 'Lobsters', 'Scallops' |
| `species_group` | TEXT | Species category | 'Pelagic', 'Demersal', 'Shellfish' |
| `live_weight_tonnes` | REAL | Catch weight | Numeric values in tonnes |
| `landed_weight_tonnes` | REAL | Landed weight | Numeric values in tonnes |
| `value_thousands` | REAL | **Value in £000s** | Multiply by 1000 for actual £ value |

### Important Data Notes

1. **Value is in thousands of pounds** - The `value_thousands` column stores values in £000s. For display, multiply by 1000 or clearly indicate the unit.

2. **"Scotland" interpretation** - When users say "Scotland", they mean `port_nationality = 'UK - Scotland'` (not vessel nationality).

3. **Price per tonne calculation** - Use: `SUM(value_thousands) * 1000 / SUM(live_weight_tonnes)`

4. **Data aggregation** - Records are pre-aggregated by month, so individual vessel trips are not available.

### Sample Data Rows

```
year|month|port           |port_nationality|species_name       |live_weight_tonnes|value_thousands
2021|1    |Plymouth       |UK - England    |Monks or Anglers   |0.1396           |0.33205
2021|1    |Plymouth       |UK - England    |Brill              |0.0033           |0.00933
2021|1    |Plymouth       |UK - England    |Crabs (C.P.Mixed)  |0.006            |0.02106
2024|3    |Peterhead      |UK - Scotland   |Mackerel           |1234.5           |2850.3
2024|3    |Peterhead      |UK - Scotland   |Herring            |567.8            |890.2
```

### Indexes

The following indexes exist for query performance:
- `idx_port` on `port`
- `idx_species` on `species_name`
- `idx_year_month` on `(year, month)`
- `idx_port_nationality` on `port_nationality`
- `idx_species_group` on `species_group`

---

## Current Implementation

### Architecture Overview

1. User enters natural language question in Streamlit text input
2. Question is sent to Claude Sonnet 4 via OpenRouter API along with SYSTEM_PROMPT
3. Claude returns SQL query (expected format: plain SQL text)
4. SQL is executed against SQLite database
5. Results are formatted and displayed in Streamlit
6. A second API call generates a natural language description of the results

### Current SYSTEM_PROMPT

This is the core prompt that guides SQL generation (from `app.py` lines 62-84):

```python
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
```

The `SCHEMA_DESCRIPTION` variable contains the column list and notes from lines 39-60 of `app.py`.

### Query Flow Code

```python
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
    except Exception as e:
        # Error handling code...
```

### Known Limitations

1. **No few-shot examples** - The prompt relies on rules rather than concrete examples
2. **Limited date handling guidance** - No explicit instructions for BETWEEN clauses or multi-year queries
3. **Ambiguous filtering** - Unclear how to handle complex WHERE conditions with multiple filters
4. **No query planning** - The model doesn't break down complex questions into steps
5. **Schema inconsistencies** - Duplicate column names might confuse the model

---

## Example Queries

### Queries That Work Well

These queries consistently produce correct SQL:

1. **Simple aggregation**
   - Question: "Which port landed the most fish in 2024?"
   - Expected SQL:
     ```sql
     SELECT port, port_nationality, ROUND(SUM(live_weight_tonnes), 2) as total_tonnes
     FROM landings
     WHERE year = 2024
     GROUP BY port, port_nationality
     ORDER BY total_tonnes DESC
     LIMIT 1
     ```

2. **Top N with single filter**
   - Question: "What are the top 5 species by value?"
   - Expected SQL:
     ```sql
     SELECT species_name, ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
     FROM landings
     GROUP BY species_name
     ORDER BY total_value_pounds DESC
     LIMIT 5
     ```

3. **Regional filter**
   - Question: "How much mackerel was landed in Scotland?"
   - Expected SQL:
     ```sql
     SELECT ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
            ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
     FROM landings
     WHERE species_name = 'Mackerel'
       AND port_nationality = 'UK - Scotland'
     ```

4. **Price calculation**
   - Question: "Average price per tonne of lobster?"
   - Expected SQL:
     ```sql
     SELECT ROUND(SUM(value_thousands) * 1000 / SUM(live_weight_tonnes), 2) as avg_price_per_tonne_pounds
     FROM landings
     WHERE species_name = 'Lobsters'
       AND live_weight_tonnes > 0
     ```

### Queries That Need Improvement

These queries fail or produce incorrect SQL:

1. **Multi-year with location filter** ⚠️ PRIMARY ISSUE
   - Question: "list top five species landed in plymouth between 2020-2022"
   - Expected SQL:
     ```sql
     SELECT species_name, ROUND(SUM(live_weight_tonnes), 2) as total_tonnes
     FROM landings
     WHERE port = 'Plymouth'
       AND year BETWEEN 2020 AND 2022
     GROUP BY species_name
     ORDER BY total_tonnes DESC
     LIMIT 5
     ```
   - **Known Result:** Scallops (6,602.90t), Monks or Anglers (627.32t), Cuttlefish (396.61t), Pilchards (392.95t), Lemon Sole (351.23t)

2. **Year-on-year comparison**
   - Question: "Compare total shellfish landings in Scotland between 2020 and 2024"
   - Expected SQL needs multiple aggregations or CASE statements

3. **Complex temporal analysis**
   - Question: "What was the trend in mackerel landings from 2015 to 2023?"
   - Expected SQL needs GROUP BY year with ordering

4. **Multiple filters with aggregation**
   - Question: "Show me monthly cod landings in English ports over 10m vessels in 2023"
   - Expected SQL:
     ```sql
     SELECT month, ROUND(SUM(live_weight_tonnes), 2) as total_tonnes
     FROM landings
     WHERE species_name = 'Cod'
       AND port_nationality = 'UK - England'
       AND length_group = 'Over10m'
       AND year = 2023
     GROUP BY month
     ORDER BY month
     ```

5. **Nested aggregations**
   - Question: "Which species had the highest average monthly value in 2024?"
   - Requires aggregation by species and month, then averaging

---

## Specific Help Needed

I need guidance on the following areas to improve the natural language to SQL conversion:

### 1. System Prompt Architecture

**Question:** How should the system prompt be restructured to better handle complex queries?

**Current Approach:** Rule-based guidance with schema description

**Alternatives to Consider:**
- Few-shot learning with 5-10 example queries?
- Chain-of-thought prompting (think step-by-step)?
- Separate prompts for query planning vs SQL generation?

### 2. Handling Multi-Condition Queries

**Question:** What's the best way to teach the model to handle queries with multiple filters across different dimensions (time, location, species)?

**Specific Issues:**
- BETWEEN clauses for year ranges
- Combining port name filters with date filters
- Understanding when to use AND vs OR in WHERE clauses

### 3. Temporal Query Patterns

**Question:** How can I improve the model's understanding of temporal queries?

**Examples:**
- "between 2020 and 2022" → `year BETWEEN 2020 AND 2022`
- "from 2015 to 2023" → `year >= 2015 AND year <= 2023`
- "in 2024" → `year = 2024`
- "last 5 years" → requires calculation from current year

### 4. Schema Ambiguity

**Question:** The database has duplicate columns with different naming conventions. Should I:
- Clean the schema before querying?
- Provide explicit guidance on which columns to use?
- Add examples showing correct column usage?

### 5. Few-Shot Examples

**Question:** If I add few-shot examples, how many and which patterns should I prioritize?

**Candidate Patterns:**
- Simple aggregation (TOP N)
- Regional filtering
- Date range queries
- Price calculations
- Multi-condition WHERE clauses

### 6. Error Handling and Fallbacks

**Question:** How can the system better detect when a query is ambiguous or impossible?

**Current Approach:** Model returns `SELECT 'Cannot answer...' as error`

**Issues:**
- Model doesn't always recognize impossible queries
- No mechanism for asking clarifying questions
- No validation before execution

### 7. Model Selection

**Question:** Is Claude Sonnet 4 the right model for this task?

**Considerations:**
- Cost vs accuracy tradeoff
- Response time requirements
- Would a larger model (Opus) handle complex queries better?
- Should I use extended thinking for planning complex queries?

---

## Full Code Listings

### File: `app.py`

Main Streamlit application with query interface and SQL generation.

```python
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
covering the period from 2008 to 2024. The dataset contains detailed records of commercial fish landings
at UK ports, including species caught, landing locations, vessel nationalities, fishing gear types,
catch weights and monetary values. You can query by specific ports, species, time periods, regional
comparisons or vessel characteristics to explore trends and patterns in UK fisheries.
""")

st.markdown("")  # Add spacing

# [... CSS styling omitted for brevity - see full app.py ...]

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
            st.subheader("Results")

            # [... formatting and display code ...]

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

# [... footer code ...]
```

### File: `query_engine.py`

Alternative implementation with more structured approach (not currently used by app.py, but shows different pattern):

```python
"""
MMO Fish Landings Query Engine

Takes natural language questions and converts them to SQL queries
against the MMO landings database.
"""

import sqlite3
import json
from anthropic import Anthropic

# Database schema description for the LLM
SCHEMA_DESCRIPTION = """
You have access to a SQLite database with UK fish landing statistics.

TABLE: landings
- year (INTEGER): Year of landing (e.g., 2024)
- month (INTEGER): Month of landing (1-12)
- port (TEXT): Name of port where fish was landed (e.g., 'Peterhead', 'Plymouth', 'Newlyn')
- port_nationality (TEXT): Which region/country the port is in. Values include:
  'UK - Scotland', 'UK - England', 'UK - Wales', 'UK - Northern Ireland',
  'UK - Isle of Man', 'UK - Channel Islands', 'Norway', 'Denmark', 'Netherlands',
  'Ireland', 'France', 'Spain', 'Belgium', 'Iceland', 'Faeroe Islands', 'Canada'
- vessel_nationality (TEXT): Nationality of the fishing vessel (same values as port_nationality)
- length_group (TEXT): Vessel size - either '10m&Under' or 'Over10m'
- gear_category (TEXT): Fishing method - e.g., 'Trawl', 'Dredges', 'Traps', 'Nets', 'Lines', 'Seines'
- species_code (TEXT): Short code for species (e.g., 'MAC' for Mackerel)
- species_name (TEXT): Full species name (e.g., 'Mackerel', 'Cod', 'Lobsters', 'Scallops')
- species_group (TEXT): Category - 'Pelagic', 'Demersal', 'Shellfish'
- live_weight_tonnes (REAL): Weight of catch in tonnes (live weight)
- landed_weight_tonnes (REAL): Weight actually landed in tonnes
- value_thousands (REAL): Value in thousands of pounds (£)

IMPORTANT NOTES:
- When users say "Scotland" they likely mean port_nationality = 'UK - Scotland'
- Value is in THOUSANDS of pounds, so multiply by 1000 or note this in your response
- For "average price per tonne", calculate SUM(value_thousands) / SUM(live_weight_tonnes) * 1000
- Use LIKE with wildcards for partial species matches (e.g., WHERE species_name LIKE '%Crab%')
- Always use ROUND() for numerical outputs
- The data currently only contains 2024 data
"""

SYSTEM_PROMPT = f"""You are a helpful assistant that converts natural language questions about UK fish landings into SQL queries.

{SCHEMA_DESCRIPTION}

When given a question:
1. First, write a brief explanation of what you understand the user is asking
2. Then provide the SQL query inside <sql></sql> tags
3. The SQL must be valid SQLite syntax

If the question cannot be answered with the available data, explain why.

Examples:

User: How much mackerel was landed in Scotland in 2024?
Assistant: You want to know the total mackerel landings (by weight and value) at Scottish ports in 2024.

<sql>
SELECT
    ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
    ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE species_name = 'Mackerel'
  AND port_nationality = 'UK - Scotland'
  AND year = 2024
</sql>

User: What are the top 5 ports for lobster?
Assistant: You want to find which ports land the most lobsters by value.

<sql>
SELECT
    port,
    port_nationality,
    ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
    ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings
WHERE species_name = 'Lobsters'
GROUP BY port, port_nationality
ORDER BY total_value_pounds DESC
LIMIT 5
</sql>

User: What's the average price per tonne of cod?
Assistant: You want to calculate the average price per tonne for cod across all landings.

<sql>
SELECT
    ROUND(SUM(value_thousands) * 1000 / SUM(live_weight_tonnes), 2) as avg_price_per_tonne_pounds
FROM landings
WHERE species_name = 'Cod'
  AND live_weight_tonnes > 0
</sql>
"""


class MMOQueryEngine:
    def __init__(self, db_path: str, api_key: str = None):
        self.db_path = db_path
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def _get_sql_from_response(self, response_text: str) -> str | None:
        """Extract SQL from between <sql> tags"""
        if '<sql>' not in response_text or '</sql>' not in response_text:
            return None
        start = response_text.index('<sql>') + 5
        end = response_text.index('</sql>')
        return response_text[start:end].strip()

    def _run_query(self, sql: str) -> tuple[list[dict], str | None]:
        """Execute SQL and return results as list of dicts"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows, None
        except Exception as e:
            return [], str(e)

    def ask(self, question: str) -> dict:
        """
        Main method: takes a natural language question, returns answer.

        Returns dict with:
        - question: the original question
        - explanation: what the LLM understood
        - sql: the generated SQL
        - results: query results (list of dicts)
        - error: any error message
        - summary: natural language summary of results
        """
        # Step 1: Get SQL from LLM
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}]
        )

        llm_response = response.content[0].text
        sql = self._get_sql_from_response(llm_response)

        # Extract explanation (everything before the SQL tags)
        explanation = llm_response.split('<sql>')[0].strip() if sql else llm_response

        if not sql:
            return {
                "question": question,
                "explanation": explanation,
                "sql": None,
                "results": [],
                "error": "Could not generate SQL query",
                "summary": explanation
            }

        # Step 2: Run the query
        results, error = self._run_query(sql)

        if error:
            return {
                "question": question,
                "explanation": explanation,
                "sql": sql,
                "results": [],
                "error": f"SQL error: {error}",
                "summary": f"Query failed: {error}"
            }

        # Step 3: Generate a natural language summary of results
        summary = self._summarise_results(question, results)

        return {
            "question": question,
            "explanation": explanation,
            "sql": sql,
            "results": results,
            "error": None,
            "summary": summary
        }

    def _summarise_results(self, question: str, results: list[dict]) -> str:
        """Generate a natural language summary of the query results"""
        if not results:
            return "No results found."

        if len(results) == 1 and len(results[0]) <= 3:
            # Simple single-row result - just format it nicely
            parts = []
            for key, value in results[0].items():
                if isinstance(value, float):
                    if 'pound' in key.lower() or 'value' in key.lower():
                        parts.append(f"{key.replace('_', ' ')}: £{value:,.2f}")
                    else:
                        parts.append(f"{key.replace('_', ' ')}: {value:,.2f}")
                else:
                    parts.append(f"{key.replace('_', ' ')}: {value}")
            return ", ".join(parts)

        # For more complex results, let the LLM summarise
        summary_prompt = f"""Given this question: "{question}"

And these query results (as JSON):
{json.dumps(results[:20], indent=2)}

Provide a brief, natural language summary of the findings. Be concise - 2-3 sentences max.
If there are monetary values, format them with £ signs and commas."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": summary_prompt}]
        )

        return response.content[0].text
```

---

## Additional Context

### Data Source

MMO publishes landing data at:
https://www.gov.uk/government/collections/uk-sea-fisheries-annual-statistics

Data is released as ODS files, which are processed by the `load_data.py` script.

### Cost Considerations

- Each query makes 2 API calls (SQL generation + result description)
- Using Claude Sonnet 4 via OpenRouter
- Typical query cost: $0.002-0.005 per complete interaction
- High-volume users would benefit from caching or query history

### User Expectations

Users expect the system to:
1. Understand common query patterns without SQL knowledge
2. Handle date ranges naturally ("between 2020 and 2022")
3. Correctly interpret regional names ("Scotland" = UK - Scotland)
4. Provide sensible defaults (TOP 10 if no limit specified)
5. Include helpful context columns in results (not just aggregated values)

---

## Summary

This tool is close to being production-ready for marine economics consultants, but the natural language to SQL conversion needs improvement to handle more sophisticated queries. The main challenge is getting the system prompt right to enable complex multi-condition queries, particularly those involving temporal ranges and multiple filters.

**Your expert guidance on improving the prompt engineering approach would be greatly appreciated!**
