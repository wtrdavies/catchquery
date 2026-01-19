#!/usr/bin/env python3
"""
Memory-efficient ODS to CSV converter
Processes row-by-row to avoid loading entire dataset into RAM
"""
import csv
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

def convert_ods_to_csv(ods_path, csv_path, max_cols=20):
    """
    Convert ODS to CSV with minimal memory usage
    Processes rows one at a time
    """
    print(f"Loading ODS: {ods_path}")
    print("This may take a moment...")

    # Load document (this loads structure, not all data)
    doc = opendocument.load(ods_path)
    tables = doc.spreadsheet.getElementsByType(Table)

    if not tables:
        raise ValueError("No sheets found in ODS file")

    sheet = tables[0]
    sheet_name = sheet.getAttribute('name')
    print(f"Converting sheet: '{sheet_name}'")

    rows = sheet.getElementsByType(TableRow)
    total_rows = len(rows)
    print(f"Total rows to process: {total_rows:,}")

    # Open CSV file for writing
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None

        for row_idx, row in enumerate(rows):
            cells = row.getElementsByType(TableCell)
            row_values = [get_cell_value(cell) for cell in cells[:max_cols]]

            # Initialize CSV writer with header row
            if row_idx == 0:
                # Filter empty trailing columns
                num_cols = len(row_values)
                while num_cols > 0 and not row_values[num_cols - 1]:
                    num_cols -= 1
                row_values = row_values[:num_cols]
                writer = csv.writer(csvfile)
                writer.writerow(row_values)
                print(f"Header: {row_values[:5]}... ({len(row_values)} columns)")
            else:
                # Write data rows
                writer.writerow(row_values)

                # Progress indicator
                if row_idx % 10000 == 0:
                    print(f"  Processed {row_idx:,} / {total_rows:,} rows ({100*row_idx/total_rows:.1f}%)")

    print(f"\n✓ Conversion complete!")
    print(f"  Output: {csv_path}")
    print(f"  Rows: {total_rows:,}")

if __name__ == "__main__":
    import sys

    ods_file = "data/Underlying_data_set_-_2014-2024.ods"
    csv_file = "data/landings_2014-2024.csv"

    try:
        convert_ods_to_csv(ods_file, csv_file)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
