# Week 7 DocuBot: requirement audit

Source: https://courses.codepath.org/courses/ai110/unit/7#!tinker

The complete current page was re-read in the cloud browser. All eight expandable
sections were explicitly opened: Why this matters, Key terms, Setup commands,
Parts 1–4, and After Class. Activity Overview, Goals, Before Class, instructions,
and every checkpoint were read as well. This is an audit of the Tinker, not a
claim that the separate Show project or course submission has been completed.

## Requirement-by-requirement mapping

| Website item | Implementation / evidence | Status |
|---|---|---|
| Overview: compare naive, retrieval only, and RAG | CLI modes 1/2/3; identical-query runner `compare_modes.py` | Implemented; generated comparisons need a key |
| Why this matters: evidence from private docs | Grounding explanation in model card and walkthrough | Documented |
| Goals: distinguish the three modes | Model card section 3 and walkthrough | Documented |
| Goals: implement document index and retrieval | `build_index`, `score_document`, `retrieve` in `docubot.py` | Implemented and tested |
| Goals: ground LLM answers in snippets | `answer_rag`, `GeminiClient.answer_from_snippets` | Integration tested; live model not tested |
| Goals: refusal and realistic developer evaluation | Refusal tests, actual saved queries, starter evaluation | Offline validation complete |
| Key terms: practice technical communication | Seven definitions in `WALKTHROUGH.md` | Written explanation ready; oral practice is for the learner |
| Setup: fork and clone starter | Personal fork; local checkout with origin pointing to it | Done |
| Setup: open in VS Code | Source is ready to open in an editor | No claim made about opening the user's local VS Code |
| Setup: virtual environment and requirements | `.venv` created and dependencies installed | Done |
| Setup: configure Gemini and start without disabled warning | No API key available | User accepted the no-key route |
| Setup: explicit no-key exception | Website allows Parts 2 and 3 fully offline | Followed; warning is expected without a key |
| Part 1: run naive mode with auth/users/database questions | Mode 1 and identical-query runner ready | Live answers unavailable without a key |
| Part 1: inspect docs and identify unsupported output | All four docs reviewed; source scope/conflicts documented | Docs review done; no fabricated naive output |
| Part 2: inspect and fill all three TODO methods | Real term-to-file index, numeric scoring, sorted top matches | Done |
| Part 2: simple, explainable design discussed with AI | Normalization, section chunking, cutoff, and ranking explained in source/model card | Done; learner should review before presenting |
| Part 2: run Mode 2 with the exact auth/users prompts | `experiments/tinker_checkpoint_results.json`; test includes “Which endpoint returns all users?” | Done |
| Part 3: smaller snippets | Heading-aware sections with filename and parent heading context | Done; website explicitly allows sections instead of paragraphs |
| Part 3: explicit “no useful context” refusal | Below 0.4 query coverage means no returned snippet; no snippets means refusal | Done and tested |
| Part 3: supported plus unrelated question | Auth question returns generation code; payment question refuses | Done; saved outputs |
| Part 4: retrieval plus LLM plus strict evidence rules | RAG prompt includes context-only answers, refusals, and filename citations | Implemented and integration tested |
| Part 4: same wording across all three modes | Each loop uses the same `query` for naive, retrieval, and RAG | Implemented; live generation pending |
| Part 4: one example of each requested behavior | Actual retrieval successes, verbosity, refusals, and lexical failures documented | Actual naive/RAG examples still need a key |
| Part 4: record observations in model card | All seven model-card sections filled; execution limits explicit | Offline observations complete |
| After Class: compare with linked solution | Reference index/scoring/chunking/guardrail/model card read after implementation | Done; comparison below |

## Checkpoint explanations

### Part 1: What was unsupported, and what evidence would retrieval add?

No live naive answer was generated, so there is no observed unsupported sentence
to quote. The relevant evidence for the token question is the Token Generation
section of AUTH.md: `generate_access_token` in `auth_utils.py`, with
`AUTH_SECRET_KEY` as the signing variable. A naive answer naming a different
function or file would need checking against that section. This is an example of
how to evaluate a future output, not an observed model failure.

### Part 2: Which query gave the clearest result, and why?

“Which endpoint returns all users?” ranks the API_REFERENCE.md `GET /api/users`
section first. Its meaningful terms are `endpoint`, normalized `return`, and
`user`; the section covers all three (coverage 1.0) and its parent heading
contains endpoint/user terms. The full endpoint section preserves the admin-only
restriction and the response example. `retrieve` performs coverage filtering and
heading-based ranking after `build_index` finds candidate files.

### Part 3: What made the guardrail trigger, and what did refusal look like?

“Is there any mention of payment processing in these docs?” has no meaningful
word overlap, after common/meta words are removed. No section reaches the 0.4
coverage threshold. `retrieve` returns `[]`, so retrieval mode returns exactly:

> I do not know based on these docs.

The same pre-generation refusal runs without calling Gemini. In contrast, the
token-generation question returns a small AUTH.md section with the function and
module names. Saved exact outputs are in the checkpoint-results JSON.

### Part 4: Which mode was easiest to trust, and what did others miss?

Only retrieval and deterministic pre-generation refusals have real observations
here. Retrieval gives inspectable source evidence; naive and generated RAG cannot
be empirically compared without an API key. Prompt tests prove which context is
sent, not whether a real model follows the instructions. The model card separates
these limits from expected behavior and supplies the live-comparison command.

## Comparison with the official solution

The reference uses an inverted index, raw keyword-overlap counts, paragraph
chunks, and a minimum score of 1. Our version uses normalized query coverage,
section chunks with parent headings, and a minimum coverage of 0.4. Sections are
an expressly permitted choice in Part 3. They keep endpoint restrictions and
user-table headings together, whereas paragraph splits can separate them.

Both approaches preserve filenames, return top snippets, and refuse when no
useful match is found. Our index actually narrows candidate files; the reference
builds an index but scans all chunks when retrieving.

Running the same starter evaluator gave the reference **5/8 = 0.625** and this
fork **7/8 = 0.875**. The evaluator counts the no-source payment query as a miss
for both even though both correctly refuse. These are filename-hit results on a
tiny known development set, not generated-answer accuracy or generalization.

A review found that the initial implementation discarded root introductions.
The updated version retains them, with a ranking penalty when detailed sections
exist. A regression test verifies that introduction-only facts remain searchable.

## Validation and CI

- 17 unit/integration tests pass locally, including the exact site prompt,
  answer evidence, refusal, threshold boundaries, introduction preservation,
  repeated-word scoring, CLI startup, and honest offline comparisons.
- The offline comparison is rerun for 11 questions. Its missing generated answers
  are labeled `NOT RUN`; its no-context RAG refusals are actual executions.
- Starter evaluation remains unmodified and its metric limitations are explicit.
- `.github/workflows/ci.yml` runs on pushes, pull requests, or manual dispatch.
  It installs dependencies, checks syntax, runs the tests (including CLI smoke),
  runs retrieval evaluation, and exercises the offline comparison on Python
  3.11 and 3.12. It requires no Gemini secret and grants only `contents: read`.
- Passing mocked prompt/integration tests does not validate live model quality.
  The assignment's real generated comparisons and verbal learner explanations
  remain distinct from the completed code and offline validation.

The first hosted run exposed a CI checkout issue: depth 1 makes Git treat the
checked-out commit as a root, so `git show --check` flags existing Markdown hard
line breaks throughout the starter. CI now fetches depth 2 to compare with the
parent, uses Node 24 action versions, and pins Ubuntu 24.04.
