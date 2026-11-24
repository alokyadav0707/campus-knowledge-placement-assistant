"""Evaluate top-10 retrieval using saved human relevance judgments."""

import argparse
import csv
from pathlib import Path

from src.ingest import ROOT
from src.search import search

EVAL_DIR = ROOT / "evaluation"
QUESTIONS = EVAL_DIR / "questions.csv"
FIELDS = ["question_id", "question", "rank", "chunk_id", "kind", "filename", "page_number", "distance", "text", "relevant"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def save_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def collect(questions, mode, db_path, search_fn=search):
    """Search once per question and keep all 10 positions for review."""
    rows = []
    for number, question in enumerate(questions, 1):
        # Query each collection separately for baselines; both uses existing search.
        if mode == "both":
            matches = search_fn(question["question"], db_path, top_k=10)
        else:
            matches = search_fn(question["question"], db_path, top_k=10, collection=mode)
        for rank, item in enumerate(matches, 1):
            meta = item["metadata"]
            rows.append({
                "question_id": question["question_id"],
                "question": question["question"],
                "rank": rank,
                "chunk_id": item["id"],
                "kind": item["kind"],
                "filename": meta.get("filename", ""),
                "page_number": meta.get("page_number", ""),
                "distance": f"{item['distance']:.4f}",
                "text": item["text"].replace("\n", " "),
                "relevant": "",
            })
        print(f"{number}/{len(questions)}: {question['question_id']} ({len(matches)} results)")
    return rows


def page_metrics(questions, rows):
    """Known gold pages measure retrieval coverage, not precision."""
    grouped = {}
    for row in rows:
        grouped.setdefault(row["question_id"], []).append(row)
    output = []
    for question in questions:
        targets = {int(page) for page in question["gold_pages"].split(";") if page.strip()}
        expected_file = question["filename"]
        matches = grouped.get(question["question_id"], [])
        ranks = [int(row["rank"]) for row in matches
                 if row["filename"] == expected_file
                 and str(row["page_number"]).isdigit()
                 and int(row["page_number"]) in targets]
        best = min(ranks) if ranks else None
        output.append({
            "question_id": question["question_id"],
            "gold_pages": question["gold_pages"],
            "first_gold_page_rank": best if best else "",
            "gold_page_hit_at_10": int(best is not None),
            "gold_page_rr": round(1 / best, 4) if best else 0,
        })
    return output


def score(questions, rows):
    """Only human-labeled records count toward true P@10."""
    grouped = {}
    for row in rows:
        grouped.setdefault(row["question_id"], []).append(row)
    per_question = []
    for question in questions:
        qid = question["question_id"]
        matches = grouped.get(qid, [])
        if any(row["relevant"].strip() not in {"0", "1"} for row in matches):
            raise ValueError(f"Incomplete 0/1 judgments for {qid}")
        if len(matches) != 10:
            raise ValueError(f"{qid} has {len(matches)} results, not 10. Cannot calculate comparable P@10.")
        relevant = sum(int(row["relevant"]) for row in matches)
        per_question.append({"question_id": qid, "relevant_in_top_10": relevant,
                             "precision_at_10": round(relevant / 10, 3)})
    mean_p10 = sum(item["precision_at_10"] for item in per_question) / len(per_question)
    return per_question, mean_p10


def main():
    parser = argparse.ArgumentParser(description="Evaluate text and table retrieval")
    parser.add_argument("action", choices=["prepare", "score"])
    parser.add_argument("--mode", choices=["both", "text", "cell"], default="both")
    parser.add_argument("--db", type=Path, default=ROOT / "data/chroma")
    args = parser.parse_args()

    questions = read_csv(QUESTIONS)
    if len(questions) != 50 or len({q["question_id"] for q in questions}) != 50:
        raise ValueError("The evaluation set must have 50 unique questions")
    judgments_file = EVAL_DIR / f"judgments_{args.mode}.csv"
    if args.action == "prepare":
        rows = collect(questions, args.mode, args.db)
        save_csv(judgments_file, rows, FIELDS)
        metrics = page_metrics(questions, rows)
        save_csv(EVAL_DIR / f"page_results_{args.mode}.csv", metrics, list(metrics[0]))
        rate = sum(row["gold_page_hit_at_10"] for row in metrics) / 50
        print(f"Gold-page Hit@10: {rate:.1%} (NOT precision@10)")
        print(f"Review the relevant column in: {judgments_file}")
    else:
        rows = read_csv(judgments_file)
        per_question, mean = score(questions, rows)
        output = EVAL_DIR / f"precision_results_{args.mode}.csv"
        save_csv(output, per_question, list(per_question[0]))
        print(f"Human-judged mean Precision@10: {mean:.1%}")
        print(f"Individual scores saved to {output}")


if __name__ == "__main__":
    main()
