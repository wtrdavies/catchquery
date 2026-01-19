#!/usr/bin/env python3
"""
Lightweight ODS inspector - extracts column headers and samples without loading full dataset
"""
from odf import opendocument
from odf.table import Table, TableRow, TableCell
from odf.text import P

def get_cell_value(cell):
    """Extract text value from a cell"""
    text_content = []
    for p in cell.getElementsByType(P):
        for node in p.childNodes:
            if hasattr(node, 'data'):
                text_content.append(str(node.data))
    return ''.join(text_content).strip()

def inspect_ods_structure(file_path, max_rows=20):
    """
    Inspect ODS file structure with minimal memory usage
    Returns: (headers, sample_rows, total_row_estimate)
    """
    print(f"Loading ODS document: {file_path}")
    doc = opendocument.load(file_path)

    tables = doc.spreadsheet.getElementsByType(Table)
    print(f"Found {len(tables)} sheet(s)")

    # Use first sheet
    sheet = tables[0]
    sheet_name = sheet.getAttribute('name')
    print(f"Inspecting sheet: '{sheet_name}'")

    rows = sheet.getElementsByType(TableRow)
    total_rows = len(rows)
    print(f"Total rows in sheet: {total_rows}")

    # Get headers from first row
    header_row = rows[0]
    header_cells = header_row.getElementsByType(TableCell)
    headers = [get_cell_value(cell) for cell in header_cells]

    # Filter out empty headers
    headers = [h for h in headers if h]

    print(f"\n=== COLUMN HEADERS ({len(headers)} columns) ===")
    for i, header in enumerate(headers, 1):
        print(f"{i}. {header}")

    # Get sample rows
    print(f"\n=== SAMPLE ROWS (up to {max_rows}) ===")
    sample_data = []
    for i in range(1, min(max_rows + 1, total_rows)):
        row = rows[i]
        cells = row.getElementsByType(TableCell)
        row_values = [get_cell_value(cell) for cell in cells[:len(headers)]]
        sample_data.append(row_values)

        if i <= 5:  # Print first 5 rows
            print(f"Row {i}: {row_values[:5]}...")  # Just first 5 values

    return headers, sample_data, total_rows

if __name__ == "__main__":
    import sys

    file_path = "data/Underlying_data_set_-_2014-2024.ods"

    try:
        headers, samples, total = inspect_ods_structure(file_path, max_rows=50)
        print(f"\n=== SUMMARY ===")
        print(f"Columns: {len(headers)}")
        print(f"Sample rows extracted: {len(samples)}")
        print(f"Total rows in file: {total:,}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
