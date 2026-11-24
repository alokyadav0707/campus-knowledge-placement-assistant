import json

import pymupdf
import pytest

from src.ingest import clean_text, extract_chunks, ingest_folder, split_into_chunks


def make_pdf(path):
    with pymupdf.open() as document:
        first = document.new_page()
        first.insert_text((50, 80), "Placement registration closes on 15 August.")
        second = document.new_page()
        second.insert_text((50, 80), "The library allows two books per student.")
        document.save(path)


def test_clean_text():
    assert clean_text("Hello \n  campus\tstudent ") == "Hello campus student"


def test_chunks_overlap():
    result = split_into_chunks("one two three four five six seven", 4, 2)
    assert result == ["one two three four", "three four five six", "five six seven"]


def test_invalid_chunk_settings():
    with pytest.raises(ValueError):
        split_into_chunks("hello world", 4, 4)


def test_extract_chunks_and_pages(tmp_path):
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf)
    chunks = extract_chunks(pdf, 120, 25)
    assert len(chunks) == 2
    assert [chunk["page_number"] for chunk in chunks] == [1, 2]
    assert chunks[0]["chunk_id"] == "sample_p1_c1"
    assert "Placement registration" in chunks[0]["text"]
    assert "library allows" in chunks[1]["text"]


def test_ingest_writes_jsonl(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_pdf(raw / "sample.pdf")

    settings = tmp_path / "settings.json"
    settings.write_text('{"chunk_size_words": 120, "chunk_overlap_words": 25}')
    sources = tmp_path / "sources.json"
    sources.write_text('[{"filename":"sample.pdf","title":"Test PDF","url":"https://example.org/test.pdf"}]')
    output = tmp_path / "chunks.jsonl"

    chunks = ingest_folder(raw, output, settings, sources)
    lines = [json.loads(line) for line in output.read_text().splitlines()]
    assert chunks == lines
    assert len(lines) == 2
    assert lines[0]["title"] == "Test PDF"
    assert lines[0]["source_url"] == "https://example.org/test.pdf"


def test_empty_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_folder(tmp_path, tmp_path / "out.jsonl", "unused", "unused")
