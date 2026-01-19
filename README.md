# MMO Fish Landings Query Tool

A natural language interface for querying UK fish landing statistics from the Marine Management Organisation.

## What it does

Ask questions in plain English like:
- "How much mackerel was landed in Scotland in 2024?"
- "What are the top 5 ports for lobster?"
- "Average price per tonne of cod?"
- "Show me monthly trends for herring"

The tool converts your question into SQL, runs it against the database, and returns the results.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare your data

Download MMO landing data from [GOV.UK](https://www.gov.uk/government/collections/uk-sea-fisheries-annual-statistics) and place the ODS/Excel files in a `data/` folder.

Then run the data loader:

```bash
python load_data.py
```

This creates `mmo_landings.db` with all your data.

### 3. Set your API key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 4. Run the web interface

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
├── app.py              # Streamlit web interface
├── query_engine.py     # Core engine (NL → SQL → Results)
├── load_data.py        # Data loading script
├── mmo_landings.db     # SQLite database (created by load_data.py)
├── requirements.txt    # Python dependencies
└── README.md
```

## Database Schema

The `landings` table contains:

| Column | Type | Description |
|--------|------|-------------|
| year | INTEGER | Year of landing |
| month | INTEGER | Month (1-12) |
| port | TEXT | Port name (e.g., 'Peterhead') |
| port_nationality | TEXT | Region ('UK - Scotland', 'UK - England', etc.) |
| vessel_nationality | TEXT | Vessel's flag state |
| length_group | TEXT | '10m&Under' or 'Over10m' |
| gear_category | TEXT | Fishing method |
| species_code | TEXT | 3-letter code |
| species_name | TEXT | Full species name |
| species_group | TEXT | 'Pelagic', 'Demersal', 'Shellfish' |
| live_weight_tonnes | REAL | Catch weight |
| landed_weight_tonnes | REAL | Landed weight |
| value_thousands | REAL | Value in £000s |

## Cost Estimates

Each query uses approximately:
- ~1,500 tokens for the system prompt + question
- ~200 tokens for the SQL response
- ~300 tokens for result summarisation (optional)

At current Claude Sonnet pricing (~$3/million input, $15/million output), each query costs roughly **£0.001-0.002** (less than a penny).

## Adding More Years of Data

The `load_data.py` script can process multiple files. Just add more ODS/Excel files to your data folder and re-run. The database handles millions of rows without issues.

## Limitations

- Only answers questions about data in the database
- Cannot make predictions or forecasts
- Complex multi-step analysis may need manual SQL
- Results depend on how the LLM interprets your question

## Extending

Ideas for future development:
- Add chart generation (matplotlib/plotly)
- Export to Excel with formatting
- Caching for repeated queries
- Query history and saved reports
- Comparison features (year-on-year, port-to-port)
