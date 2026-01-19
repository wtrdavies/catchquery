# MMO Fish Landings Query Tool

## Project Overview

A natural language interface for querying UK fish landing statistics from the Marine Management Organisation (MMO). Users ask questions in plain English (e.g., "Which port landed the most mackerel in 2024?") and get answers back, with the system automatically generating and executing SQL queries against a SQLite database.

## Target Users

Marine economics consultants and researchers who need to quickly interrogate MMO landing data without writing SQL themselves. The tool should save time on routine data queries and make the data more accessible to non-technical users.

## Current State

Working prototype with:
- SQLite database loaded with 2024 MMO landing data (~64,000 rows)
- Streamlit web interface
- Natural language to SQL conversion via Claude (through OpenRouter API)
- Basic query execution and results display

## Tech Stack

- **Python 3.9+**
- **SQLite** - local database storing MMO landing records
- **Streamlit** - web interface
- **OpenRouter API** - routes to Claude for NL-to-SQL conversion
- **Pandas** - data manipulation

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit web interface - main entry point |
| `query_engine.py` | Core logic for NL → SQL → Results (not currently used by app.py, but contains useful patterns) |
| `load_data.py` | Script to load MMO ODS/Excel files into SQLite |
| `mmo_landings.db` | SQLite database with landing data |

## Database Schema

Single table called `landings`:

```sql
CREATE TABLE landings (
    year INTEGER,
    month INTEGER,
    port TEXT,                    -- e.g., 'Peterhead', 'Plymouth', 'Newlyn'
    port_nationality TEXT,        -- 'UK - Scotland', 'UK - England', 'UK - Wales', etc.
    vessel_nationality TEXT,      -- flag state of vessel
    length_group TEXT,            -- '10m&Under' or 'Over10m'
    gear_category TEXT,           -- 'Trawl', 'Dredges', 'Traps', 'Nets', etc.
    species_code TEXT,            -- 3-letter code, e.g., 'MAC' for Mackerel
    species_name TEXT,            -- full name, e.g., 'Mackerel', 'Cod', 'Lobsters'
    species_group TEXT,           -- 'Pelagic', 'Demersal', 'Shellfish'
    live_weight_tonnes REAL,      -- catch weight in tonnes
    landed_weight_tonnes REAL,    -- landed weight in tonnes
    value_thousands REAL          -- value in £000s (multiply by 1000 for actual £)
);
```

Indexes exist on: `port`, `species_name`, `year/month`, `port_nationality`, `species_group`.

## Data Notes

- Value is stored in **thousands of pounds** – remember to multiply by 1000 or note this in outputs
- "Scotland" in user queries means `port_nationality = 'UK - Scotland'`
- ~174 different species, ~509 ports
- Currently only 2024 data loaded; will expand to 2014-2024

## How the NL-to-SQL Works

1. User enters question in Streamlit text box
2. Question sent to Claude via OpenRouter with a system prompt containing the schema
3. Claude returns SQL query
4. SQL executed against SQLite database
5. Results displayed in Streamlit

The system prompt in `app.py` (variable `SYSTEM_PROMPT`) tells Claude about the schema and how to interpret common queries.

## Known Issues / Limitations

- No chart generation yet
- No query history or caching
- Error messages could be more user-friendly
- System prompt could be improved for edge cases
- No validation that generated SQL is safe (though SQLite is read-only in practice)

## Future Development Ideas

1. **Add more years of data** - load 2014-2024 from MMO archives
2. **Chart generation** - automatically create visualisations for trend queries
3. **Query caching** - avoid repeated API calls for same questions
4. **Better error handling** - catch and explain common query failures
5. **Export options** - download results as CSV/Excel
6. **Comparison features** - year-on-year, port-to-port comparisons
7. **Cost tracking** - show users estimated API cost per query
8. **Authentication** - if deploying for multiple clients

## Data Source

MMO publishes landing data at:
https://www.gov.uk/government/collections/uk-sea-fisheries-annual-statistics

Data is released as ODS files. The `load_data.py` script processes these into SQLite.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenRouter API key
export OPENROUTER_API_KEY="your-key"

# Run the app
streamlit run app.py
```

Then open http://localhost:8501

## Example Queries That Work Well

- "Which port landed the most fish in 2024?"
- "What are the top 5 species by value?"
- "How much mackerel was landed in Scotland?"
- "Average price per tonne of lobster?"
- "Show me landings in Plymouth by species"
- "Compare shellfish landings between England and Scotland"

## Example Queries That Might Need Improvement

- Queries about trends (no multi-year data yet)
- Very specific vessel queries (data is aggregated)
- Questions requiring joins or complex subqueries
