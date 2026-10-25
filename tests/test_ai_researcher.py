from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import ai_researcher


class CorpusTests(unittest.TestCase):
    def test_builtin_corpus_is_valid(self) -> None:
        documents = ai_researcher.load_corpus()
        self.assertEqual(len(documents), 10)
        self.assertEqual(len({document.id for document in documents}), 10)

    def test_custom_corpus_is_loaded(self) -> None:
        payload = {
            "documents": [
                {
                    "id": "x1",
                    "title": "Edge Inference",
                    "tags": ["ml", "edge"],
                    "content": "Quantization reduces model size for edge deployment.",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            documents = ai_researcher.load_corpus(path)
        self.assertEqual(documents[0].title, "Edge Inference")
        self.assertEqual(documents[0].tags, ("ml", "edge"))

    def test_duplicate_ids_are_rejected(self) -> None:
        payload = [
            {"id": "a", "title": "A", "tags": [], "content": "text"},
            {"id": "a", "title": "B", "tags": [], "content": "text"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ai_researcher.CorpusError):
                ai_researcher.load_corpus(path)


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = ai_researcher.load_corpus()

    def test_tokenize_removes_stopwords_and_normalizes(self) -> None:
        self.assertEqual(ai_researcher.tokenize("The RAG and the Model!"), ["rag", "model"])

    def test_exact_title_match_ranks_first(self) -> None:
        hits = ai_researcher.search("retrieval augmented generation", self.documents)
        self.assertEqual(hits[0].document.id, "d4")
        self.assertIn("retrieval", hits[0].matched_terms)

    def test_top_k_is_respected(self) -> None:
        hits = ai_researcher.search("ai", self.documents, top_k=2)
        self.assertEqual(len(hits), 2)

    def test_empty_query_returns_no_hits(self) -> None:
        self.assertEqual(ai_researcher.search("the and of", self.documents), [])

    def test_empty_summary_is_well_formed(self) -> None:
        result = ai_researcher.summarize("quantum basket weaving", self.documents)
        self.assertEqual(result.found, 0)
        self.assertEqual(result.summary, "")
        self.assertEqual(result.sources, ())


class CliTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = ai_researcher.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_topics(self) -> None:
        code, stdout, _ = self.run_cli(["topics"])
        self.assertEqual(code, 0)
        self.assertIn("Retrieval Augmented Generation", stdout)

    def test_search_json(self) -> None:
        code, stdout, _ = self.run_cli(["search", "transformers", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload[0]["id"], "d1")
        self.assertGreater(payload[0]["score"], 0)

    def test_summarize_plain_text(self) -> None:
        code, stdout, _ = self.run_cli(["summarize", "retrieval", "generation"])
        self.assertEqual(code, 0)
        self.assertIn("Summary:", stdout)
        self.assertIn("Open questions:", stdout)

    def test_missing_corpus_is_reported(self) -> None:
        code, _, stderr = self.run_cli(["--corpus", "/does/not/exist.json", "topics"])
        self.assertEqual(code, 2)
        self.assertIn("corpus not found", stderr)


if __name__ == "__main__":
    unittest.main()
