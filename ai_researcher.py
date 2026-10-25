#!/usr/bin/env python3
"""AI Researcher - a dependency-free research corpus assistant.

Search, rank, and summarize documents from a local JSON corpus. The tool ships
with a small built-in corpus and also accepts a custom corpus file, which makes
it useful as a standalone CLI or as a reference implementation for a larger
retrieval pipeline.

Examples:
    python ai_researcher.py topics
    python ai_researcher.py search "retrieval augmented generation"
    python ai_researcher.py summarize "efficient fine tuning" --json
    python ai_researcher.py --corpus examples/sample_corpus.json search "rag"

Custom corpus format (either form is accepted):
    {"documents": [{"id": "...", "title": "...", "tags": ["..."], "content": "..."}]}
    [{"id": "...", "title": "...", "tags": ["..."], "content": "..."}]

License: MIT
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__version__ = "1.0.0"

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

BUILTIN_DOCUMENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "d1",
        "title": "Transformers",
        "tags": ["ai", "nlp", "attention"],
        "content": (
            "Transformer models replace recurrence with self-attention, enabling "
            "parallel training and long-range dependencies. BERT and GPT families "
            "build on this architecture."
        ),
    },
    {
        "id": "d2",
        "title": "Diffusion Models",
        "tags": ["ai", "generative", "images"],
        "content": (
            "Diffusion models learn to reverse a noise process. DDPM and "
            "score-matching variants produce high-quality images and audio."
        ),
    },
    {
        "id": "d3",
        "title": "RLHF",
        "tags": ["ai", "alignment", "training"],
        "content": (
            "Reinforcement learning from human feedback trains a reward model on "
            "human preferences, then optimizes a policy with PPO or DPO."
        ),
    },
    {
        "id": "d4",
        "title": "Retrieval Augmented Generation",
        "tags": ["ai", "rag", "retrieval"],
        "content": (
            "RAG combines a retriever over a document index with a generator, "
            "improving factual accuracy and reducing hallucination."
        ),
    },
    {
        "id": "d5",
        "title": "Vector Databases",
        "tags": ["ai", "infra", "retrieval"],
        "content": (
            "Vector databases store embeddings and support approximate nearest "
            "neighbour search using HNSW, IVF, and product quantization."
        ),
    },
    {
        "id": "d6",
        "title": "Multi-Agent Systems",
        "tags": ["ai", "agents", "orchestration"],
        "content": (
            "Multi-agent systems coordinate specialized agents with tools, memory, "
            "and protocols to solve complex tasks."
        ),
    },
    {
        "id": "d7",
        "title": "Mixture of Experts",
        "tags": ["ai", "efficiency", "scale"],
        "content": (
            "Mixture-of-experts layers route tokens to a subset of parameters, "
            "scaling models without proportional compute cost."
        ),
    },
    {
        "id": "d8",
        "title": "Chain of Thought",
        "tags": ["ai", "reasoning", "prompting"],
        "content": (
            "Chain-of-thought prompting encourages step-by-step reasoning, "
            "improving performance on math and logic benchmarks."
        ),
    },
    {
        "id": "d9",
        "title": "Fine-tuning and LoRA",
        "tags": ["ai", "training", "efficiency"],
        "content": (
            "Low-rank adaptation fine-tunes large models by training small adapter "
            "matrices, drastically reducing compute and memory."
        ),
    },
    {
        "id": "d10",
        "title": "Evaluation of LLMs",
        "tags": ["ai", "evaluation", "benchmarks"],
        "content": (
            "LLM evaluation includes static benchmarks, pairwise preference tests, "
            "and automated judges with rubric-based scoring."
        ),
    },
)


class CorpusError(ValueError):
    """Raised when a corpus file is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class Document:
    """A single searchable document."""

    id: str
    title: str
    tags: tuple[str, ...]
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "tags": list(self.tags),
            "content": self.content,
        }


@dataclass(frozen=True)
class SearchHit:
    """A ranked document with its relevance score and matched terms."""

    document: Document
    score: int
    matched_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.document.to_dict(),
            "score": self.score,
            "matched_terms": list(self.matched_terms),
        }


@dataclass(frozen=True)
class Summary:
    """An extractive summary with sources and follow-up questions."""

    query: str
    found: int
    summary: str
    sources: tuple[SearchHit, ...]
    open_questions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "found": self.found,
            "summary": self.summary,
            "sources": [hit.to_dict() for hit in self.sources],
            "open_questions": list(self.open_questions),
        }


def tokenize(text: str) -> list[str]:
    """Normalize text into lowercase alphanumeric tokens without stopwords."""
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def _token_set(text: str) -> set[str]:
    return set(tokenize(text))


def _parse_document(raw: Any, position: int) -> Document:
    if not isinstance(raw, dict):
        raise CorpusError(f"document {position} must be a JSON object")

    doc_id = raw.get("id")
    title = raw.get("title")
    tags = raw.get("tags")
    content = raw.get("content")

    if not isinstance(doc_id, str) or not doc_id.strip():
        raise CorpusError(f"document {position} has an invalid 'id'")
    if not isinstance(title, str) or not title.strip():
        raise CorpusError(f"document {position} has an invalid 'title'")
    if not isinstance(content, str) or not content.strip():
        raise CorpusError(f"document {position} has an invalid 'content'")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise CorpusError(f"document {position} has an invalid 'tags' list")

    return Document(
        id=doc_id.strip(),
        title=title.strip(),
        tags=tuple(tag.strip() for tag in tags if tag.strip()),
        content=content.strip(),
    )


def load_corpus(path: Path | None = None) -> list[Document]:
    """Load documents from a JSON file, or use the built-in corpus."""
    if path is None:
        raw_documents: Any = list(BUILTIN_DOCUMENTS)
    else:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CorpusError(f"corpus not found: {path}") from exc
        except OSError as exc:
            raise CorpusError(f"cannot read corpus {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CorpusError(f"invalid JSON in {path}: {exc}") from exc

        if isinstance(payload, dict):
            raw_documents = payload.get("documents")
        else:
            raw_documents = payload

    if not isinstance(raw_documents, list) or not raw_documents:
        raise CorpusError("corpus must contain a non-empty 'documents' list")

    documents = [
        _parse_document(raw, position) for position, raw in enumerate(raw_documents, start=1)
    ]
    ids = [document.id for document in documents]
    if len(ids) != len(set(ids)):
        raise CorpusError("document ids must be unique")

    return documents


def score_document(query_tokens: Sequence[str], document: Document) -> tuple[int, tuple[str, ...]]:
    """Score a document with field weighting and a small exact-phrase bonus."""
    query_set = set(query_tokens)
    if not query_set:
        return 0, ()

    title_tokens = _token_set(document.title)
    tag_tokens = _token_set(" ".join(document.tags))
    body_tokens = _token_set(document.content)

    matched = tuple(sorted(query_set & (title_tokens | tag_tokens | body_tokens)))
    score = (
        4 * len(query_set & title_tokens)
        + 2 * len(query_set & tag_tokens)
        + len(query_set & body_tokens)
    )

    query_phrase = " ".join(query_tokens)
    title_phrase = " ".join(tokenize(document.title))
    body_phrase = " ".join(tokenize(document.content))
    if len(query_tokens) > 1 and query_phrase in title_phrase:
        score += 3
    elif len(query_tokens) > 1 and query_phrase in body_phrase:
        score += 1

    return score, matched


def search(
    query: str,
    documents: Sequence[Document],
    top_k: int = 3,
) -> list[SearchHit]:
    """Return the highest-scoring documents for a query."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    hits: list[SearchHit] = []
    for document in documents:
        score, matched = score_document(query_tokens, document)
        if score > 0:
            hits.append(SearchHit(document=document, score=score, matched_terms=matched))

    hits.sort(key=lambda hit: (-hit.score, hit.document.title.lower(), hit.document.id))
    return hits[:top_k]


def _best_sentences(hit: SearchHit, limit: int = 2) -> list[str]:
    sentences = [part.strip() for part in SENTENCE_RE.split(hit.document.content) if part.strip()]
    if not sentences:
        return []

    terms = set(hit.matched_terms)
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (-len(terms & _token_set(item[1])), item[0]),
    )
    selected = [sentence for _, sentence in ranked[:limit]]
    return selected or sentences[:1]


def summarize(query: str, documents: Sequence[Document], top_k: int = 3) -> Summary:
    """Build an extractive summary from the best matching documents."""
    hits = search(query, documents, top_k=top_k)
    if not hits:
        return Summary(
            query=query,
            found=0,
            summary="",
            sources=(),
            open_questions=(),
        )

    sentences: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        for sentence in _best_sentences(hit, limit=2):
            normalized = sentence.lower()
            if normalized not in seen:
                seen.add(normalized)
                sentences.append(sentence)
        if len(sentences) >= 4:
            break

    questions: list[str] = []
    for hit in hits[:2]:
        questions.append(f'What evidence supports the claims in "{hit.document.title}"?')
    if len(hits) >= 2:
        questions.append(
            f'How does "{hits[0].document.title}" compare with "{hits[1].document.title}"?'
        )
    if hits:
        questions.append(f'Which benchmark would best validate "{hits[0].document.title}"?')

    return Summary(
        query=query,
        found=len(hits),
        summary=" ".join(sentences[:4]),
        sources=tuple(hits),
        open_questions=tuple(questions[:3]),
    )


def render_topics(documents: Sequence[Document]) -> str:
    """Render a compact table of all documents."""
    id_width = max(2, *(len(document.id) for document in documents))
    title_width = max(5, *(len(document.title) for document in documents))
    lines = [f"{'ID':<{id_width}}  {'TITLE':<{title_width}}  TAGS"]
    for document in documents:
        lines.append(
            f"{document.id:<{id_width}}  {document.title:<{title_width}}  "
            f"{', '.join(document.tags)}"
        )
    return "\n".join(lines)


def render_search(hits: Sequence[SearchHit]) -> str:
    """Render ranked search results."""
    if not hits:
        return "No results."

    lines = []
    for hit in hits:
        tags = ", ".join(hit.document.tags)
        lines.append(f"{hit.score:>3}  {hit.document.title}  [{tags}]")
        if hit.matched_terms:
            lines.append(f"     matched: {', '.join(hit.matched_terms)}")
    return "\n".join(lines)


def render_summary(result: Summary) -> str:
    """Render a summary report as plain text."""
    if result.found == 0:
        return f"No results for: {result.query}"

    lines = [f"Query: {result.query}", "", "Summary:", result.summary, "", "Sources:"]
    for hit in result.sources:
        lines.append(f"- {hit.document.title} (score {hit.score}): {hit.document.content}")
    if result.open_questions:
        lines.extend(["", "Open questions:"])
        lines.extend(f"- {question}" for question in result.open_questions)
    return "\n".join(lines)


def _dump_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _emit(text: str, out_path: Path | None) -> None:
    if out_path is None:
        print(text)
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_researcher",
        description="Search and summarize a local research corpus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python ai_researcher.py search "retrieval augmented generation"\n'
            '  python ai_researcher.py summarize "efficient fine tuning" --json\n'
            "  python ai_researcher.py --corpus examples/sample_corpus.json topics"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=None,
        metavar="PATH",
        help="JSON corpus file (default: built-in corpus)",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    topics = commands.add_parser("topics", help="list all documents")
    topics.add_argument("--json", action="store_true", help="emit JSON")

    search_cmd = commands.add_parser("search", help="search the corpus")
    search_cmd.add_argument("query", nargs="+", help="query terms")
    search_cmd.add_argument("--top", "-k", type=int, default=3, metavar="N", help="max results")
    search_cmd.add_argument("--json", action="store_true", help="emit JSON")
    search_cmd.add_argument("--out", type=Path, metavar="PATH", help="write output to a file")

    summarize_cmd = commands.add_parser("summarize", help="summarize matching documents")
    summarize_cmd.add_argument("query", nargs="+", help="query terms")
    summarize_cmd.add_argument(
        "--top", "-k", type=int, default=3, metavar="N", help="max source documents"
    )
    summarize_cmd.add_argument("--json", action="store_true", help="emit JSON")
    summarize_cmd.add_argument("--out", type=Path, metavar="PATH", help="write output to a file")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        documents = load_corpus(args.corpus)
    except CorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "topics":
        if args.json:
            output = _dump_json([document.to_dict() for document in documents])
        else:
            output = render_topics(documents)
        _emit(output, None)
        return 0

    query = " ".join(args.query).strip()
    if not query:
        parser.error("query must not be empty")

    try:
        if args.command == "search":
            hits = search(query, documents, top_k=args.top)
            payload = [hit.to_dict() for hit in hits]
            output = _dump_json(payload) if args.json else render_search(hits)
            _emit(output, args.out)
        elif args.command == "summarize":
            result = summarize(query, documents, top_k=args.top)
            output = _dump_json(result.to_dict()) if args.json else render_summary(result)
            _emit(output, args.out)
        else:  # pragma: no cover - argparse enforces the command list
            parser.error(f"unknown command: {args.command}")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
