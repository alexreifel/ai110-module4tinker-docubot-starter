"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in sorted(glob.glob(pattern)):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    # Common question/function words should not make unrelated docs look relevant.
    STOP_WORDS = set("a an the is are was were be been do does did how what where which when why who i you me my we our it its this that these those in on at to of for from by with and or any all there mention based docs document documents please can could would should stored required".split())
    MIN_QUERY_COVERAGE = 0.4

    @classmethod
    def tokenize(cls, text):
        """Normalize punctuation/case and a few inflections, not word meaning."""
        words = re.findall(r"[a-z0-9_]+", text.lower())
        tokens = set()
        for word in words:
            if word in cls.STOP_WORDS:
                continue
            # Keep configuration names and identifiers intact.
            if "_" not in word:
                for suffix in ("ions", "ion", "ing", "ed", "s"):
                    if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                        word = word[:-len(suffix)]
                        break
            tokens.add(word)
        return tokens

    def build_index(self, documents):
        """Map normalized terms to filenames; retain small, heading-aware chunks.

        Markdown sections preserve endpoint headings alongside their response
        examples, and table headings alongside their rows. Plain text is split
        at blank lines. No LLM or vector database is needed.
        """
        index = {}
        self.chunks = []
        self.intro_chunks = set()
        for filename, text in documents:
            for token in self.tokenize(text):
                index.setdefault(token, []).append(filename)
            if re.search(r"^#{1,6} ", text, flags=re.MULTILINE):
                headings, body, sections = [], [], []

                def save_section():
                    # Preserve introductory evidence, but lower its rank when
                    # more specific subsections exist. Never silently drop text.
                    body_text = "\n".join(body).strip()
                    if body_text:
                        section = ("\n".join(h for _, h in headings)
                                   + "\n\n" + body_text).strip()
                        sections.append(section)
                        if len(headings) <= 1:
                            self.intro_chunks.add((filename, section))

                for line in text.splitlines():
                    match = re.match(r"^(#{1,6}) ", line)
                    if match:
                        save_section()
                        level = len(match.group(1))
                        headings = [(n, h) for n, h in headings if n < level]
                        headings.append((level, line))
                        body = []
                    else:
                        body.append(line)
                save_section()
                if len(sections) == 1:
                    # A standalone section should not be penalized as an intro.
                    self.intro_chunks.discard((filename, sections[0]))
                if not sections:
                    sections = [text]
            else:
                sections = re.split(r"\n\s*\n", text)
            for section in sections:
                section = section.strip()
                if section:
                    self.chunks.append((filename, section))
        return index

    def score_document(self, query, text):
        """Fraction of distinct meaningful query terms found in this snippet.

        A score is lexical overlap, not a probability that the answer is right.
        """
        query_terms = self.tokenize(query)
        if not query_terms:
            return 0.0
        return len(query_terms & self.tokenize(text)) / len(query_terms)

    def retrieve(self, query, top_k=3):
        """Return up to top_k sections with >=40% meaningful-term coverage.

        The inverted index narrows candidate files. Zero/weak matches are
        excluded, so both retrieval and RAG can refuse before generation.
        Ties preserve sorted file order and source section order.
        """
        if top_k <= 0:
            return []
        candidates = set()
        for token in self.tokenize(query):
            candidates.update(self.index.get(token, []))
        scored = []
        for filename, text in self.chunks:
            if filename in candidates:
                score = self.score_document(query, text)
                if score >= self.MIN_QUERY_COVERAGE:
                    # Prefer direct section-title matches among similar passages.
                    heading = "\n".join(line for line in text.splitlines()
                                        if line.startswith("#"))
                    rank = score + 0.25 * self.score_document(query, heading)
                    if (filename, text) in self.intro_chunks:
                        rank *= 0.5
                    scored.append((rank, filename, text))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [(filename, text) for _, filename, text in scored[:top_k]]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        snippets = self.retrieve(query, top_k=top_k)
        if not snippets:
            return "I do not know based on these docs."
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )
        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
