"""Save actual identical-query comparisons; --live enables Gemini calls."""
import argparse
import json
from pathlib import Path

from dataset import SAMPLE_QUERIES
from docubot import DocuBot


def compare(live=False):
    client = None
    if live:
        from dotenv import load_dotenv
        from llm_client import GeminiClient
        load_dotenv()
        client = GeminiClient()  # Missing key fails clearly; never fake answers.
    bot = DocuBot(llm_client=client)
    rows = []
    queries = SAMPLE_QUERIES + [
        "How do I rotate the database encryption key?",
        "How do I sign in?",
        "What is the capital of France?",
    ]
    for query in queries:
        snippets = bot.retrieve(query)
        row = {
            "query": query,
            "retrieval": bot.answer_retrieval_only(query),
            "sources": [name for name, _ in snippets],
            "naive": "NOT RUN: Gemini API key required.",
            "rag": "NOT RUN: Gemini API key required.",
        }
        if live:
            row["naive"] = client.naive_answer_over_full_docs(query, bot.full_corpus_text())
            row["rag"] = bot.answer_rag(query)
        elif not snippets:
            row["rag"] = bot.answer_rag(query)  # Real pre-generation refusal.
        rows.append(row)
    return {"live_gemini": live, "results": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", default="experiments/offline_comparison.json")
    args = parser.parse_args()
    result = compare(args.live)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Saved {len(result['results'])} comparisons to {destination} (live={args.live})")
