from src.rag import NO_ANSWER, answer_question, make_context


def sample_matches():
    return [
        {
            "text": "258 pre-placement offers were accepted.",
            "metadata": {"filename": "placement.pdf", "page_number": 10},
            "kind": "text",
        }
    ]


def test_context_has_page_citation():
    context, sources = make_context(sample_matches())
    assert "[1] placement.pdf, PDF page 10" in context
    assert len(sources) == 1


def test_answer_uses_retrieved_evidence():
    def fake_search(question, db_path, top_k):
        return sample_matches()

    def fake_generate(question, context):
        assert "258 pre-placement offers" in context
        return "258 PPOs were accepted [1]."

    answer, citations = answer_question(
        "How many PPOs were accepted?", search_fn=fake_search, generate_fn=fake_generate
    )
    assert answer == "258 PPOs were accepted [1]."
    assert citations[0][1]["metadata"]["page_number"] == 10


def test_empty_search_does_not_call_llm():
    def fake_search(question, db_path, top_k):
        return []

    def fake_generate(question, context):
        raise AssertionError("LLM should not be called without evidence")

    answer, citations = answer_question("unknown", search_fn=fake_search, generate_fn=fake_generate)
    assert answer == NO_ANSWER
    assert citations == []
