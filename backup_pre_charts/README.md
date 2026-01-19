# Pre-Charts Backup

**Date**: 2026-01-19
**Purpose**: Backup of working version before adding chart visualization feature

## What's in this backup

This directory contains the clean, working version of the MMO Fish Landings Query Tool **before** chart integration:

- `app.py` - Streamlit application with table-only results display
- `requirements.txt` - Python dependencies (no Plotly)
- `CLAUDE.md` - Project documentation

## Why this backup exists

The tool works perfectly with styled data tables. Before adding automatic chart generation (using Plotly), we created this backup to preserve the simpler, table-only version.

## How to restore this version

If you want to revert to the table-only version:

```bash
# From the landings_tool directory
cp backup_pre_charts/app.py .
cp backup_pre_charts/requirements.txt .
cp backup_pre_charts/CLAUDE.md .

# Reinstall dependencies (removes plotly)
pip install -r requirements.txt

# Restart the app
streamlit run app.py
```

## Features in this version

✓ Natural language to SQL query conversion
✓ Styled data tables with maritime theme
✓ Query result summaries via Claude
✓ CSV export functionality
✓ Empty result suggestions
✓ 2014-2024 MMO landing data (580,854 rows)
✓ Standardized nationality formats

**No charts** - Results displayed as tables only
