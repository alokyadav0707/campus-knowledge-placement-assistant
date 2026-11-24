"""Prepare PDF citations for display in the app."""

from pathlib import Path


def group_citations(citations):
    grouped = {}
    for number, match in citations:
        meta = match["metadata"]
        filename = Path(meta["filename"]).name
        page = meta["page_number"]
        key = (filename, page)
        if key not in grouped:
            grouped[key] = {
                "filename": filename,
                "page": page,
                "numbers": [],
                "text": match["text"],
            }
        grouped[key]["numbers"].append(number)
    return list(grouped.values())
