# Campus Knowledge & Placement Assistant

Ask questions about indexed campus PDFs. The app retrieves relevant PDF text and table cells from **ChromaDB**, sends retrieved context to a **Groq-hosted LLM**, and displays answers with PDF page citations.

## Stack

- Python 3.11, PyMuPDF (PDF text), pdfplumber/Camelot (tables), pandas (CSVs)
- SentenceTransformers `all-MiniLM-L6-v2` (local embeddings)
- ChromaDB (persistent text and table-cell collections)
- Groq API with `openai/gpt-oss-120b` (answer generation)
- Streamlit (chat interface), pytest (tests)

Text extraction, indexing and retrieval are local. **Question answering sends the question and selected PDF excerpts to Groq's API.** A network connection and a Groq API key are required for generation. Check provider usage limits yourself.

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` in the project root (see `.env.example`):

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Never commit your `.env` file. The `.gitignore` excludes it and local generated data.

## Documents and indexing

Place downloaded PDFs in `data/raw/`. The source URL configuration lives in `config/sources.json`; you may also download a PDF manually. The project was developed using an IIT Bombay placement report. Check usage rights before sharing PDFs publicly.

Run these commands **only for initial indexing or when the source PDFs change**:

```powershell
python -m src.ingest
python -m src.tables
python -m src.index
```

The outputs include `data/processed/chunks.jsonl`, `data/processed/cells.jsonl`, table CSVs in `data/processed/tables/`, and persistent Chroma collections in `data/chroma/`. Table extraction may miss or incorrectly parse tables, so inspect the CSVs. Scanned-image PDFs need OCR, which is not implemented here.

## Run the project

Once documents are indexed:

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit (typically `http://localhost:8501`). Type a question in the chat box. Retrieved evidence is shown under expandable PDF citations. If the PDF is present in `data/raw/`, you can download it from the app. You can also use the CLI:

```powershell
python -m src.search "How many PPOs were accepted?" --top-k 5
python -m src.rag "How many PPOs were accepted?"
```

Chat history lasts for the current Streamlit session; it is not written to disk. LLM answers can still be wrong: citation numbers are checked against retrieved sources, **but facts are not automatically verified**. Citations reference physical PDF page positions (starting at 1), which may differ from printed page numbers. The interface does not yet open the PDF directly at a page.

## Evaluation (50 questions)

`evaluation/questions.csv` contains the 50-question set. Retrieval is evaluated separately from generated-answer correctness.

```powershell
python -m src.evaluate prepare
# Manually fill relevant=1 or relevant=0 for each row of evaluation/judgments_both.csv
python -m src.evaluate score
```

The script prints the **human-judged mean Precision@10** and saves scores in `evaluation/precision_results_both.csv`. It also reports gold-page Hit@10 separately. For the text-only comparison use `--mode text` on both commands and label its judgments separately.

**No numerical evaluation score is claimed in this README:** read the actual score produced by your run, and retain the labeled judgments and evaluation configuration so it can be reproduced. The evaluation does not establish an answer hallucination rate.

## Tests

```powershell
python -m pytest -q
```

The tests include extraction, vector-index logic using test doubles, retrieval/evaluation functions, RAG prompt/citation behavior, and UI citation grouping. API integration and PDF extraction quality should also be checked on the actual machine. If a table extraction test fails because the PDF test fixture is old, use `src/create_demo_pdf.py` from Part 2 of the project (not Part 1).

## Code map

| File | Purpose |
|---|---|
| `src/ingest.py` | PyMuPDF page text -> chunks with page metadata |
| `src/tables.py` | Tables -> normalized CSV and contextualized cell records |
| `src/index.py` | Embeddings -> text and table-cell Chroma collections |
| `src/search.py` | Top-k semantic retrieval from one or both collections |
| `src/rag.py` | Retrieval -> evidence prompt -> Groq answer and citations |
| `src/evaluate.py` | Retrieve 50 questions, export judgments, calculate Precision@10 |
| `src/display.py` | Group repeated citations from the same PDF page |
| `app.py` | Streamlit UI and in-session chat history |

## Limitations and possible improvements

The LLM gets a small subset of retrieved passages. This can miss evidence, and retrieved text may be inaccurate after PDF extraction. The system currently has no OCR, reranker, authentication, permanent chat memory, or formal citation entailment checker. PDFs and ChromaDB remain on the local laptop, but selected snippets are transmitted to Groq. Do not use confidential documents without permission.
