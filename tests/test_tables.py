import csv
import json

from src.create_demo_pdf import create_demo_pdf
from src.tables import extract_tables, normalize_header, prepare_table


def test_normalized_headers():
    used = set()
    assert [normalize_header(value, i + 1, used) for i, value in enumerate(
        ["Accepted Offers", "Accepted Offers", "", "CTC (LPA)"]
    )] == ["accepted_offers", "accepted_offers_2", "column_3", "ctc_lpa"]


def test_prepare_table():
    headers, rows = prepare_table([["Dept", "Offers"], ["CS", "42"], ["", ""]])
    assert headers == ["dept", "offers"]
    assert rows == [["CS", "42"]]
    assert prepare_table([["Not a table"]]) is None


def test_real_pdf_table_to_csv_and_cells(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    create_demo_pdf(raw / "demo_synthetic.pdf")
    source = tmp_path / "sources.json"
    source.write_text("[]")
    records_file = tmp_path / "cells.jsonl"
    records = extract_tables(raw, tmp_path / "tables", records_file, source)
    table = tmp_path / "tables/demo_synthetic_p2_t1.csv"
    assert table.exists()
    with table.open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows == [
        ["department", "offers_accepted", "median_ctc"],
        ["Computer Science", "42", "14.5 LPA"],
        ["Mechanical", "27", "8.0 LPA"],
    ]
    assert any(record["page_number"] == 2 and record["value"] == "42" for record in records)
    assert any("department: Computer Science" in record["text"] for record in records)
    assert len(records) == len([json.loads(line) for line in records_file.read_text().splitlines()])
