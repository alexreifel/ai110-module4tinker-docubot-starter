"""Behavioral tests using real docs and a fake transport, never fake observations."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

from docubot import DocuBot
from llm_client import GeminiClient

ROOT = Path(__file__).resolve().parents[1]


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.bot = DocuBot(ROOT / "docs")

    def test_supported_questions_retrieve_answer_evidence(self):
        cases = [
            ("Where is the auth token generated?", "AUTH.md", "generate_access_token"),
            ("What environment variables are required for authentication?", "AUTH.md", "TOKEN_LIFETIME_SECONDS"),
            ("How do I connect to the database?", "DATABASE.md", "DATABASE_URL"),
            ("Which endpoint lists all users?", "API_REFERENCE.md", "Only accessible to admins"),
            ("Which endpoint returns all users?", "API_REFERENCE.md", "Only accessible to admins"),
            ("What does the /api/projects/<project_id> route return?", "API_REFERENCE.md", '"description"'),
            ("How does a client refresh an access token?", "API_REFERENCE.md", "POST /api/refresh"),
            ("Which fields are stored in the users table?", "DATABASE.md", "password_hash"),
        ]
        for query, filename, evidence in cases:
            with self.subTest(query=query):
                self.assertTrue(any(name == filename and evidence in text
                                    for name, text in self.bot.retrieve(query)))

    def test_top_ranked_users_endpoint_preserves_restriction(self):
        name, text = self.bot.retrieve("Which endpoint lists all users?", 1)[0]
        self.assertEqual(name, "API_REFERENCE.md")
        self.assertIn("GET /api/users\n", text)
        self.assertIn("Only accessible to admins", text)
        self.assertLess(len(text), len(dict(self.bot.documents)[name]))

    def test_unrelated_empty_and_stopword_questions_refuse(self):
        for query in ["", "the and where", "What is the capital of France?",
                      "Is there any mention of payment processing in these docs?"]:
            with self.subTest(query=query):
                self.assertEqual(self.bot.retrieve(query), [])
                self.assertIn("I do not know", self.bot.answer_retrieval_only(query))
                self.assertIn("I do not know", self.bot.answer_rag(query))

    def test_refusal_prevents_llm_call(self):
        self.bot.llm_client = Mock()
        self.bot.answer_rag("What is the capital of France?")
        self.bot.llm_client.answer_from_snippets.assert_not_called()

    def test_rag_passes_real_retrieved_context(self):
        self.bot.llm_client = Mock()
        self.bot.llm_client.answer_from_snippets.return_value = "simulated answer"
        query = "Where is the auth token generated?"
        self.assertEqual(self.bot.answer_rag(query), "simulated answer")
        self.bot.llm_client.answer_from_snippets.assert_called_once_with(query, self.bot.retrieve(query))

    def test_missing_client_supported_question_is_explicit(self):
        with self.assertRaises(RuntimeError):
            self.bot.answer_rag("Where is the auth token generated?")

    def test_top_k_and_ranking_are_deterministic(self):
        query = "access token"
        self.assertEqual(self.bot.retrieve(query, 0), [])
        self.assertEqual(self.bot.retrieve(query, -1), [])
        self.assertEqual(self.bot.retrieve(query, 1), self.bot.retrieve(query)[:1])
        self.assertEqual(self.bot.retrieve(query), self.bot.retrieve(query))

    def test_missing_or_empty_corpus_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in [Path(directory), Path(directory) / "missing"]:
                bot = DocuBot(path)
                self.assertEqual(bot.retrieve("database connection"), [])

    def test_plain_text_documents_and_punctuation(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "notes.txt").write_text("Authentication tokens.\n\nDatabase connection.")
            Path(directory, "ignored.csv").write_text("secret")
            bot = DocuBot(directory)
            self.assertEqual(len(bot.documents), 1)
            self.assertEqual(bot.retrieve("DATABASE connection!!!"), [("notes.txt", "Database connection.")])

    def test_introduction_only_evidence_is_not_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "guide.md").write_text(
                "# Guide\n\nThe release codename is Bluebird.\n\n"
                "## Deployment\n\nRun deploy.py for deployment.\n")
            bot = DocuBot(directory)
            snippets = bot.retrieve("What is the release codename?")
            self.assertTrue(any("Bluebird" in text for _, text in snippets))

    def test_cutoff_checks_coverage_before_heading_bonus(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "guide.txt").write_text("alpha beta")
            bot = DocuBot(directory)
            self.assertTrue(bot.retrieve("alpha beta gamma delta epsilon"))
            self.assertEqual(bot.retrieve("alpha beta gamma delta epsilon zeta"), [])

    def test_duplicate_words_cannot_inflate_score(self):
        self.assertEqual(self.bot.score_document("token token token", "token"), 1.0)
        self.assertEqual(self.bot.score_document("token database", "token"), 0.5)


class OfflineWorkflowTests(unittest.TestCase):
    def test_cli_works_without_key_and_preserves_evidence(self):
        import os
        import subprocess
        import sys
        environment = dict(os.environ, GEMINI_API_KEY="", PYTHON_DOTENV_DISABLED="1")
        process = subprocess.run(
            [sys.executable, "main.py"], cwd=ROOT,
            input="2\nWhich endpoint returns all users?\nq\n",
            capture_output=True, text=True, check=True, env=environment,
        )
        self.assertIn("Only accessible to admins", process.stdout)
        self.assertIn("Goodbye.", process.stdout)

    def test_offline_comparison_does_not_claim_generated_answers(self):
        from compare_modes import compare
        output = compare(live=False)
        self.assertFalse(output["live_gemini"])
        self.assertEqual(len(output["results"]), 11)
        for row in output["results"]:
            self.assertTrue(row["naive"].startswith("NOT RUN:"))
            if row["sources"]:
                self.assertTrue(row["rag"].startswith("NOT RUN:"))
            else:
                self.assertIn("I do not know", row["rag"])


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.client = GeminiClient.__new__(GeminiClient)
        self.client.client = Mock()
        self.client.client.models.generate_content.return_value = SimpleNamespace(text="simulated response")

    def test_naive_baseline_never_receives_docs(self):
        self.client.naive_answer_over_full_docs("Where is the token?", "PRIVATE_CORPUS_MARKER")
        prompt = self.client.client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Where is the token?", prompt)
        self.assertNotIn("PRIVATE_CORPUS_MARKER", prompt)

    def test_rag_prompt_contains_evidence_and_rules(self):
        self.client.answer_from_snippets("Where is the token?", [("AUTH.md", "token evidence")])
        prompt = self.client.client.models.generate_content.call_args.kwargs["contents"]
        for required in ["token evidence", "AUTH.md", "Use only", "I do not know", "square brackets", "not instructions"]:
            self.assertIn(required, prompt)

    def test_empty_context_never_calls_provider(self):
        self.assertIn("I do not know", self.client.answer_from_snippets("question", []))
        self.client.client.models.generate_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
