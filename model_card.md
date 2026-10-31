# DocuBot Model Card

## 1. System Overview

DocuBot answers developer questions about the sample documentation in `docs/`.
It compares a no-context Gemini baseline, lexical retrieval, and retrieval plus
Gemini. It does not train a new model or implement the backend described in the
documents.

Inputs: a user question; local `.md`/`.txt` documentation; optional
`GEMINI_API_KEY` for modes 1 and 3. Outputs: source-labelled snippets, a generated
answer, or an explicit refusal. API errors are operational failures, not answers.

## 2. Retrieval Design

- Read files in sorted order for repeatable ties.
- Normalize case/punctuation, discard common question words, and strip a small
  set of inflection suffixes. Preserve underscore identifiers.
- Build an inverted index from normalized words to filenames.
- Split Markdown at headings, retaining parent headings with each section. This
  keeps endpoint restrictions, examples, and table rows with their context.
  Retain root introductions but halve their ranking when detailed subsections exist. Plain text
  uses blank-line chunks.
- Score each section by the fraction of distinct meaningful query terms matched.
  Require at least 0.4 coverage, then rank with a small heading-match bonus
  (`coverage + 0.25 * heading_coverage`). Return at most three sections.

The threshold is a transparent teaching heuristic, not a calibrated confidence
probability. A section can match words without containing an answer. Heading
context improves retrieval but can also contribute irrelevant matches. This is
small-scale keyword search, not semantic search. Section sizes are not bounded;
very large sections would need further splitting.

## 3. Use of the LLM (Gemini)

- **Naive:** send only the question. The inherited method name
  `naive_answer_over_full_docs` is retained for compatibility, but its corpus
  argument is deliberately ignored, matching the Tinker specification. The
  starter README and CLI labels incorrectly described this as full-document mode;
  those descriptions were corrected.
- **Retrieval only:** no model call; show source filenames and section text.
- **RAG:** retrieve first; refuse immediately if there are no qualifying snippets.
  Otherwise send the question and snippets to Gemini.

The RAG prompt requires answers supported by snippets, filename citations, and an
explicit refusal when evidence is insufficient. It asks the model to flag
conflicting documentation and treat embedded instructions as data. These are
prompt instructions, not guarantees or a complete prompt-injection defense.

## 4. Experiments and Comparisons

**Execution status:** retrieval and pre-generation refusals were actually run.
Live Gemini was not run because no API key was configured. Tests use a simulated
transport solely to verify prompt construction and calls; simulated outputs are
not model observations. Therefore Parts 1 and 4 still need their live-generation
observations before the entire Tinker can be called complete.

Actual outputs for 11 questions are saved in
`experiments/offline_comparison.json`. Identical query strings are used for all
three modes. Missing results are explicitly marked `NOT RUN`.

| Query | Naive | Retrieval: observed | RAG: observed |
|---|---|---|---|
| Where is the auth token generated? | Not run | Top section gives `generate_access_token` in `auth_utils.py` and signing configuration. | Not run |
| How do I connect to the database? | Not run | Top three include `DATABASE_URL` and connection examples. The overview may rank first. | Not run |
| Which endpoint lists all users? | Not run | Top section gives `GET /api/users`, including the admin-only restriction. | Not run |
| How does a client refresh an access token? | Not run | Client workflow and API refresh section appear, but docs conflict about expired-token handling. | Not run |
| Which fields are stored in the users table? | Not run | First section includes the user table and `password_hash`. | Not run |
| Is there any mention of payment processing in these docs? | Not run | Refuses: no qualifying context. | Actual pre-generation refusal; no Gemini call. |
| What is the capital of France? | Not run | Refuses: no qualifying context. | Actual pre-generation refusal; no Gemini call. |

The unmodified starter evaluation reports **7/8 = 0.875** source hits. All seven
questions with expected sources hit at top 3. The eighth, payment processing,
has no expected source and is always counted as a miss even when correctly
refused. This is a filename metric, not answer correctness. Its substring labels
also make the users-table question accept either API_REFERENCE.md or DATABASE.md.
Our tests additionally require concrete answer evidence from the correct source.
The tiny development set is not an independent generalization benchmark.

Expected patterns to check live, **not observed results**: naive output may sound
plausible without evidence; retrieval can be verifiable but verbose; RAG may
summarize retrieved evidence clearly but can still misuse it or fail to refuse.

Run the pending comparison with a locally configured key:

```bash
python compare_modes.py --live --output experiments/live_comparison.json
```

Then inspect the saved answers, replace the pending table cells, and record one
specific ungrounded naive answer, one clearer RAG answer, and one actual RAG
failure. The script saves outputs, not correctness judgments. Do not substitute
predictions for observations.

## 5. Failure Cases and Guardrails

1. **Observed irrelevant retrieval:** “How do I rotate the database encryption
   key?” retrieves authentication key-rotation advice even though the docs do not
   describe database encryption-key rotation. Shared words clear the threshold.
   The correct generated behavior is to refuse unsupported instructions. Live
   RAG's handling has not been observed.
2. **Observed weak semantic match:** “How do I sign in?” retrieves token-generation
   material instead of reliably prioritizing the login endpoint. Keyword matching
   conflates signing a token with signing in. Semantic retrieval or reranking
   could improve this, but still needs evaluation.
3. **Observed conflicting source text:** AUTH.md says to refresh when a token
   expires, while API_REFERENCE.md says `/api/refresh` exchanges an existing valid
   token. Retrieving both does not resolve the contradiction. The model should
   flag it, and maintainers should clarify the docs. No live RAG behavior is claimed.

Refuse when no relevant passages exist (payments, geography) or when retrieved
passages do not support the requested fact (database encryption-key rotation).
Only the first condition is enforced deterministically; the second relies on
Gemini following the prompt. Empty/stopword-only queries and empty/missing corpora
also refuse. Positive `top_k`, bounded result count, readable thresholds, and
source labels make behavior easier to inspect.

## 6. Limitations and Future Improvements

1. Keyword matching misses paraphrases and can overvalue misleading shared terms.
2. A matching file or section does not prove answer support; refusal can be wrong
   in either direction.
3. Stale/conflicting docs remain stale/conflicting after retrieval.
4. No live generated-answer evaluation has been completed in this environment.
5. Snippets may contain sensitive data; RAG sends selected text to the provider.

Improvements: evaluate hybrid/semantic search plus reranking; tune chunk sizes
and thresholds on a separate labeled set; check citations and claim support on
live answers, including adversarial and conflicting-document cases.

## 7. Responsible Use

Incorrect authentication advice could weaken security, and incorrect database
instructions could cause data loss. A filename citation is only useful if the
cited passage supports the claim.

- Verify answers against the actual source and running code before acting.
- Preserve access restrictions such as the admin-only users endpoint.
- Avoid sending private credentials or unauthorized documents to the provider.
- Treat refusal, unsupported answers, and contradictory docs as reasons to inspect
  the evidence rather than repeatedly prompting for a confident response.

## Validation and assistance

Implementation and documentation were prepared with Codex assistance. Seventeen
unit/integration tests pass, covering seven supported questions, refusal behavior,
chunk context, CLI-independent retrieval, missing corpora, top-k, and LLM prompt
boundaries. A CLI smoke test also passed with no API key. No claim is made that
Alex personally attended the session, observed live Gemini outputs, or authored
this implementation without assistance.

## Requirement audit and CI

See `TINKER_CHECKLIST.md` for every website section and checkpoint, including
the explicit no-key exception. GitHub Actions runs the offline tests, CLI smoke
test, starter evaluation, and comparison on Python 3.11 and 3.12.
