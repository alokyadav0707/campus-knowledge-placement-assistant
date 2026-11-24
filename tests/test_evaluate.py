import csv

import pytest

from src.evaluate import collect, page_metrics, read_csv, save_csv, score, QUESTIONS


def sample_questions():
    return [{"question_id": "Q01", "question": "How many PPOs?", "filename": "report.pdf", "gold_pages": "11"}]


def fake_search(question, db_path, top_k=10, collection="both"):
    return [{"id": f"chunk-{number}", "kind": "text", "text": f"Evidence {number}",
             "metadata": {"filename": "report.pdf", "page_number": 11 if number == 3 else 6},
             "distance": number / 100} for number in range(1, 11)]


def test_questions_have_fifty_unique_ids():
    questions = read_csv(QUESTIONS)
    assert len(questions) == 50
    assert len({q["question_id"] for q in questions}) == 50
    assert all(q["gold_pages"] and q["expected_answer"] for q in questions)


def test_collect_and_page_metrics():
    rows = collect(sample_questions(), "both", "unused", fake_search)
    assert len(rows) == 10
    assert all(row["relevant"] == "" for row in rows)
    metric = page_metrics(sample_questions(), rows)[0]
    assert metric["first_gold_page_rank"] == 3
    assert metric["gold_page_hit_at_10"] == 1


def test_precision_uses_human_judgments_not_page():
    rows = collect(sample_questions(), "both", "unused", fake_search)
    for i, row in enumerate(rows):
        row["relevant"] = "1" if i < 7 else "0"
    results, mean = score(sample_questions(), rows)
    assert mean == 0.7
    assert results[0]["relevant_in_top_10"] == 7


def test_unlabeled_rows_are_not_scored():
    rows = collect(sample_questions(), "both", "unused", fake_search)
    with pytest.raises(ValueError, match="Incomplete"):
        score(sample_questions(), rows)


def test_missing_results_not_counted_as_full_precision():
    rows = collect(sample_questions(), "both", "unused", fake_search)[:7]
    for row in rows:
        row["relevant"] = "1"
    with pytest.raises(ValueError, match="not 10"):
        score(sample_questions(), rows)


def test_save_and_read(tmp_path):
    path = tmp_path / "results.csv"
    save_csv(path, [{"question_id": "Q01", "relevant": "1"}], ["question_id", "relevant"])
    assert read_csv(path) == [{"question_id": "Q01", "relevant": "1"}]


def test_collect_single_collection():
    observed = []
    def capture(question, db_path, top_k=10, collection="both"):
        observed.append(collection)
        return fake_search(question, db_path, top_k, collection)
    collect(sample_questions(), "text", "unused", capture)
    assert observed == ["text"]
