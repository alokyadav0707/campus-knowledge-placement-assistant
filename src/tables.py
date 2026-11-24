"""Extract PDF tables into readable CSV files and cell records."""

import argparse
import csv
import json
import re
from pathlib import Path

import pdfplumber

from src.ingest import ROOT, load_sources


def clean_cell(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_header(value, position, used):
    name = re.sub(r"[^a-z0-9]+", "_", clean_cell(value).lower()).strip("_")
    name = name or f"column_{position}"
    base = name
    number = 2
    while name in used:
        name = f"{base}_{number}"
        number += 1
    used.add(name)
    return name


def prepare_table(raw_rows):
    """Return (headers, rows), skipping empty rows and unusable tables."""
    rows = [[clean_cell(cell) for cell in row] for row in raw_rows if row]
    rows = [row for row in rows if any(row)]
    if len(rows) < 2:
        return None
    width = max(len(row) for row in rows)
    if width < 2:
        return None
    rows = [(row + [""] * width)[:width] for row in rows]
    used = set()
    headers = [normalize_header(cell, i + 1, used) for i, cell in enumerate(rows[0])]
    data = [row for row in rows[1:] if any(row)]
    if not data:
        return None
    return headers, data


def extract_page_tables(pdf_path, page_number, plumber_page):
    """Use pdfplumber first; try Camelot Stream if no table is found."""
    tables = plumber_page.extract_tables() or []
    if any(prepare_table(table) for table in tables):
        return tables, "pdfplumber"

    try:
        import camelot
        found = camelot.read_pdf(str(pdf_path), pages=str(page_number), flavor="stream")
        return [table.df.values.tolist() for table in found], "camelot_stream"
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"Camelot skipped {pdf_path.name} page {page_number}: {error}")
        return [], "none"


def extract_tables(input_dir, output_dir, records_file, sources_file):
    pdf_files = sorted(Path(input_dir).glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files in {input_dir}")

    sources = load_sources(sources_file)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records_file = Path(records_file)
    records_file.parent.mkdir(parents=True, exist_ok=True)
    records = []
    table_count = 0

    for pdf_path in pdf_files:
        source = sources.get(pdf_path.name, {})
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                raw_tables, method = extract_page_tables(pdf_path, page_number, page)
                table_on_page = 0
                for raw_table in raw_tables:
                    prepared = prepare_table(raw_table)
                    if prepared is None:
                        continue
                    headers, rows = prepared
                    table_on_page += 1
                    table_count += 1
                    table_id = f"{pdf_path.stem}_p{page_number}_t{table_on_page}"
                    csv_path = output_dir / f"{table_id}.csv"
                    with csv_path.open("w", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)
                        writer.writerow(headers)
                        writer.writerows(rows)

                    for row_index, row in enumerate(rows, 1):
                        row_context = ", ".join(
                            f"{header}: {value}" for header, value in zip(headers, row) if value
                        )
                        for column_index, (header, value) in enumerate(zip(headers, row), 1):
                            if not value:
                                continue
                            records.append({
                                "cell_id": f"{table_id}_r{row_index}_c{column_index}",
                                "table_id": table_id,
                                "document_id": pdf_path.stem,
                                "filename": pdf_path.name,
                                "title": source.get("title", pdf_path.stem),
                                "source_url": source.get("url", ""),
                                "page_number": page_number,
                                "row_number": row_index,
                                "column_name": header,
                                "column_number": column_index,
                                "value": value,
                                "text": f"{source.get('title', pdf_path.stem)}. Table {table_on_page}. "
                                        f"Row {row_index}. {row_context}. "
                                        f"Column {header}: {value}",
                                "csv_file": csv_path.name,
                                "extraction_method": method,
                            })
        print(f"{pdf_path.name}: finished table extraction")

    with records_file.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Saved {table_count} tables, {len(records)} non-empty cell records")
    return records


def main():
    parser = argparse.ArgumentParser(description="Extract tables and per-cell records")
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/processed/tables")
    parser.add_argument("--records", type=Path, default=ROOT / "data/processed/cells.jsonl")
    parser.add_argument("--sources", type=Path, default=ROOT / "config/sources.json")
    args = parser.parse_args()
    extract_tables(args.input, args.output_dir, args.records, args.sources)


if __name__ == "__main__":
    main()
