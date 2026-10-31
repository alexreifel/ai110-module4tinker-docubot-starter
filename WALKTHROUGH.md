# Explaining the DocuBot Tinker

## The lesson in a minute

An LLM cannot reliably answer questions about files it has never seen. RAG first
searches those files, then gives the relevant passages to the model. This changes
what information the model can use without training a new model. It can improve
accuracy and make answers inspectable, but poor search, stale documents, and
unsupported generation still cause errors.

## Walk through the implementation

1. `DocuBot.__init__` loads local Markdown/text files and calls `build_index`.
2. `tokenize` removes punctuation and common question words, normalizes case and
   a few word endings, and keeps configuration identifiers intact.
3. `build_index` maps terms to filenames. It also makes section-sized snippets,
   keeping parent headings so a user table remains associated with database
   tables and an endpoint retains its route, restrictions, and response example.
4. `score_document` measures distinct query-word coverage. It is a match score,
   not confidence that the answer is true.
5. `retrieve` uses the index to narrow candidate files, rejects snippets below
   40% coverage, adds a heading-match ranking bonus, and returns at most three.
6. `answer_retrieval_only` displays these passages with filenames.
7. `answer_rag` refuses before calling Gemini if no snippets qualify. Otherwise,
   `answer_from_snippets` asks Gemini to answer only from evidence and cite files.
8. Mode 1 deliberately receives no docs. Its old method name is misleading,
   but this behavior is retained to match the lab's no-context baseline.

## Demonstration

```bash
python main.py
```

Choose mode 2 and ask “Which endpoint lists all users?” Show that the first
snippet includes both `GET /api/users` and the admin-only restriction. This is
more useful than an answer that merely mentions a users endpoint.

Ask “Is there any mention of payment processing in these docs?” Show the refusal.
Then ask “How do I rotate the database encryption key?” Show the irrelevant
retrieval result. Explain why a lexical threshold is insufficient to determine
whether the question is answerable.

## Validation and remaining work

Run `python -m unittest discover -s tests -v`. The tests check answer evidence,
source restrictions, refusal without model calls, and that naive mode excludes
context while RAG includes it. Mocked responses only test integration.

Run `python evaluation.py`. Its 0.875 score counts a correct payment-question
refusal as a miss. Seven supported queries have source hits at top 3. Neither
number measures generated answer truth.

Once a Gemini key is configured, run:

```bash
python compare_modes.py --live --output experiments/live_comparison.json
```

Use those real outputs to finish the model card. Compare the exact same question
in all modes. Explain an unsupported naive response, a useful raw snippet, a
clear grounded RAG answer, and a real RAG failure. Those live observations have
not yet been collected. The offline artifact labels them as not run.
