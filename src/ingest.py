"""Read PDF pages and save overlapping text chunks as JSON Lines."""

import argparse
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def clean_text(text):
    """Collapse whitespace while keeping the original words and numbers."""
    return re.sub(r"\s+", " ", text).strip()


def split_into_chunks(text, chunk_size, overlap):
    """Split words into chunks, repeating a few words between neighbors."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= overlap < chunk_size")

    words = text.split()
    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(words), step):
        part = words[start:start + chunk_size]
        if part:
            chunks.append(" ".join(part))
        if start + chunk_size >= len(words):
            break
    return chunks


def load_sources(path):
    if not Path(path).exists():
        return {}
    sources = json.loads(Path(path).read_text(encoding="utf-8"))
    return {item["filename"]: item for item in sources}


def extract_chunks(pdf_path, chunk_size, overlap, source=None):
    """Return a list of dictionaries, each pointing to one PDF page."""
    pdf_path = Path(pdf_path)
    source = source or {}
    records = []

    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            # sort=True gives a more useful reading order for many PDFs.
            text = clean_text(page.get_text("text", sort=True))
            if not text:
                print(f"No selectable text: {pdf_path.name}, page {page_index + 1}")
                continue

            parts = split_into_chunks(text, chunk_size, overlap)
            for chunk_index, content in enumerate(parts):
                records.append({
                    "chunk_id": f"{pdf_path.stem}_p{page_index + 1}_c{chunk_index + 1}",
                    "document_id": pdf_path.stem,
                    "filename": pdf_path.name,
                    "title": source.get("title", pdf_path.stem),
                    "source_url": source.get("url", ""),
                    "page_number": page_index + 1,
                    "chunk_index": chunk_index + 1,
                    "text": content,
                })
    return records


def ingest_folder(input_dir, output_file, settings_file, sources_file):
    settings = json.loads(Path(settings_file).read_text(encoding="utf-8"))
    sources = load_sources(sources_file)
    pdf_files = sorted(Path(input_dir).glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {input_dir}")

    all_chunks = []
    for pdf_path in pdf_files:
        chunks = extract_chunks(
            pdf_path,
            settings["chunk_size_words"],
            settings["chunk_overlap_words"],
            sources.get(pdf_path.name),
        )
        all_chunks.extend(chunks)
        print(f"{pdf_path.name}: {len(chunks)} text chunks")

    if not all_chunks:
        raise ValueError("No selectable text found. Scanned PDFs need OCR.")

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file:
        for chunk in all_chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Saved {len(all_chunks)} chunks to {output_file}")
    return all_chunks


def main():
    parser = argparse.ArgumentParser(description="Extract page-level PDF text chunks")
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/chunks.jsonl")
    parser.add_argument("--settings", type=Path, default=ROOT / "config/settings.json")
    parser.add_argument("--sources", type=Path, default=ROOT / "config/sources.json")
    args = parser.parse_args()
    ingest_folder(args.input, args.output, args.settings, args.sources)


if __name__ == "__main__":
    main()
