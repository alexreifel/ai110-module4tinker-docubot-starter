# DocuBot

DocuBot is a small documentation assistant that helps answer developer questions about a codebase.
It can operate in three different modes:

1. **Naive LLM mode**
   Sends only the question to Gemini, without documentation. This deliberately ungrounded baseline illustrates the need for retrieval.

2. **Retrieval only mode**
   Uses a simple indexing and scoring system to retrieve relevant snippets without calling an LLM.

3. **RAG mode (Retrieval Augmented Generation)**
   Retrieves relevant snippets, then asks Gemini to answer using only those snippets.

The docs folder contains realistic developer documents (API reference, authentication notes, database notes), but these files are **just text**. They support retrieval experiments and do not require students to set up any backend systems.

---

## Setup

### 1. Install Python dependencies

    pip install -r requirements.txt

### 2. Configure environment variables

Copy the example file:

    cp .env.example .env

Then edit `.env` to include your Gemini API key:

    GEMINI_API_KEY=your_api_key_here

If you do not set a Gemini key, you can still run retrieval only mode.

---

## Running DocuBot

Start the program:

    python main.py

Choose a mode:

- **1**: Naive LLM (no documentation context)
- **2**: Retrieval only (no LLM)
- **3**: RAG (retrieval + Gemini)

You can use built in sample queries or type your own.

---

## Running Retrieval Evaluation (optional)

    python evaluation.py

This prints simple retrieval hit rates for sample queries.

---

## Modifying the Project

You will primarily work in:

- `docubot.py`
  Implement or improve the retrieval index, scoring, and snippet selection.

- `llm_client.py`
  Adjust the prompts and behavior of LLM responses.

- `dataset.py`
  Add or change sample queries for testing.

---

## Requirements

- Python 3.9+
- A Gemini API key for LLM features (only needed for modes 1 and 3)
- No database, no server setup, no external services besides LLM calls

## Completed retrieval implementation

The three retrieval TODOs are implemented with an inverted index, normalized
keyword coverage, heading-aware chunks, a 40% coverage cutoff, and a heading
ranking bonus. See `model_card.md` for the design and observed limitations.

```bash
python -m unittest discover -s tests -v
python evaluation.py
python compare_modes.py
# After configuring GEMINI_API_KEY in your local .env:
python compare_modes.py --live --output experiments/live_comparison.json
```

`compare_modes.py` saves real outputs for the same 11 queries. Offline runs
explicitly mark missing Gemini results; they do not fabricate a comparison.
The live comparison and manual interpretation remain pending until a key is
configured. An answer containing an API-error message is not a successful test.

Read `WALKTHROUGH.md` for a presentation guide. The documents describe a fictional
backend; you do not need to set up its database or authentication server.
