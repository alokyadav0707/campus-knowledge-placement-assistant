from src.display import group_citations


def test_citations_from_same_page_are_grouped():
    citations = [
        (2, {"metadata": {"filename": "placement.pdf", "page_number": 11}, "text": "PPO table"}),
        (3, {"metadata": {"filename": "placement.pdf", "page_number": 11}, "text": "PPO count"}),
        (4, {"metadata": {"filename": "placement.pdf", "page_number": 12}, "text": "Other stats"}),
    ]
    result = group_citations(citations)
    assert len(result) == 2
    assert result[0]["numbers"] == [2, 3]
    assert result[0]["page"] == 11
    assert result[1]["page"] == 12


def test_citation_filename_is_safe():
    citations = [(1, {"metadata": {"filename": "../placement.pdf", "page_number": 2}, "text": "x"})]
    assert group_citations(citations)[0]["filename"] == "placement.pdf"
