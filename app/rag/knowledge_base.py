from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("sakura.ai.knowledge")

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_SUPPORTED_SUFFIXES = {".txt", ".md"}
_MAX_CHUNK_CHARS = 800
_MIN_CHUNK_CHARS = 40
_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    text: str
    chunk_index: int


@dataclass(frozen=True)
class KnowledgeSearchResult:
    source: str
    text: str
    score: float
    chunk_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "text": self.text,
            "score": round(self.score, 4),
            "chunk_index": self.chunk_index,
        }


class KnowledgeBase:
    """本地文档知识库：分块索引 + 语义/关键词混合检索。"""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.knowledge_dir = self.base_dir / "data" / "knowledge"
        self._chunks: list[KnowledgeChunk] = []
        self._embeddings: list[list[float]] | None = None
        self._embedder: Any = None
        self._embedding_model = DEFAULT_EMBEDDING_MODEL
        self._index_mtime: float | None = None

    def reload(self, *, force: bool = False) -> int:
        """扫描 data/knowledge 并重建索引。"""
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        latest_mtime = self._directory_mtime()
        if not force and self._chunks and self._index_mtime == latest_mtime:
            return len(self._chunks)

        chunks: list[KnowledgeChunk] = []
        for path in sorted(self.knowledge_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("读取知识库文件失败：%s (%s)", path, exc)
                continue
            rel_source = str(path.relative_to(self.knowledge_dir)).replace("\\", "/")
            for index, chunk_text in enumerate(_split_text(text)):
                normalized = chunk_text.strip()
                if len(normalized) < _MIN_CHUNK_CHARS:
                    continue
                chunks.append(
                    KnowledgeChunk(
                        source=rel_source,
                        text=normalized[:_MAX_CHUNK_CHARS],
                        chunk_index=index,
                    )
                )

        self._chunks = chunks
        self._embeddings = None
        self._embedder = None
        self._index_mtime = latest_mtime
        logger.info("知识库已索引 %s 个片段", len(self._chunks))
        return len(self._chunks)

    def search(self, query: str, *, limit: int = 5) -> list[KnowledgeSearchResult]:
        query = query.strip()
        if not query:
            return []
        if not self._chunks:
            self.reload()

        limit = max(1, min(limit, 20))
        vector_scores = self._vector_scores(query)
        keyword_scores = _keyword_scores(query, self._chunks)
        combined: list[KnowledgeSearchResult] = []
        for index, chunk in enumerate(self._chunks):
            score = 0.72 * vector_scores[index] + 0.28 * keyword_scores[index]
            if score <= 0:
                continue
            combined.append(
                KnowledgeSearchResult(
                    source=chunk.source,
                    text=chunk.text,
                    score=score,
                    chunk_index=chunk.chunk_index,
                )
            )
        combined.sort(key=lambda item: item.score, reverse=True)
        return combined[:limit]

    def format_context(self, query: str, *, limit: int = 3, max_chars: int = 2400) -> str:
        hits = self.search(query, limit=limit)
        if not hits:
            return ""
        lines = ["【知识库检索结果】"]
        total = 0
        for hit in hits:
            block = f"- [{hit.source}#{hit.chunk_index}] (相关度 {hit.score:.2f})\n{hit.text}"
            if total + len(block) > max_chars:
                break
            lines.append(block)
            total += len(block)
        return "\n".join(lines).strip()

    def list_sources(self) -> list[str]:
        if not self._chunks:
            self.reload()
        sources = sorted({chunk.source for chunk in self._chunks})
        return sources

    def source_chunk_counts(self) -> dict[str, int]:
        if not self._chunks:
            self.reload()
        counts: dict[str, int] = {}
        for chunk in self._chunks:
            counts[chunk.source] = counts.get(chunk.source, 0) + 1
        return counts

    def _directory_mtime(self) -> float:
        if not self.knowledge_dir.exists():
            return 0.0
        latest = self.knowledge_dir.stat().st_mtime
        for path in self.knowledge_dir.rglob("*"):
            if path.is_file():
                latest = max(latest, path.stat().st_mtime)
        return latest

    def _vector_scores(self, query: str) -> list[float]:
        if not self._chunks:
            return []
        if not self._ensure_embeddings():
            return [0.0] * len(self._chunks)
        assert self._embedder is not None and self._embeddings is not None
        query_vector = self._embedder.encode(query, normalize_embeddings=True)
        scores: list[float] = []
        for vector in self._embeddings:
            scores.append(float(_cosine_similarity(query_vector, vector)))
        max_score = max(scores) if scores else 0.0
        if max_score <= 0:
            return [0.0] * len(scores)
        return [score / max_score for score in scores]

    def _ensure_embeddings(self) -> bool:
        if self._embeddings is not None:
            return True
        if not self._chunks:
            return False
        try:
            if self._embedder is None:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(self._embedding_model)
            texts = [chunk.text for chunk in self._chunks]
            self._embeddings = self._embedder.encode(texts, normalize_embeddings=True)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("知识库语义嵌入不可用，将回退关键词检索：%s", exc)
            self._embeddings = None
            return False


def _split_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if not paragraphs:
        return []
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= _MAX_CHUNK_CHARS:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        if len(paragraph) <= _MAX_CHUNK_CHARS:
            buffer = paragraph
            continue
        for offset in range(0, len(paragraph), _MAX_CHUNK_CHARS):
            chunks.append(paragraph[offset : offset + _MAX_CHUNK_CHARS])
        buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def _keyword_scores(query: str, chunks: list[KnowledgeChunk]) -> list[float]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return [0.0] * len(chunks)
    scores: list[float] = []
    for chunk in chunks:
        chunk_tokens = _tokenize(chunk.text)
        if not chunk_tokens:
            scores.append(0.0)
            continue
        overlap = len(query_tokens & chunk_tokens)
        scores.append(overlap / len(query_tokens))
    max_score = max(scores) if scores else 0.0
    if max_score <= 0:
        return scores
    return [score / max_score for score in scores]


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text) if len(token) >= 2}


def _cosine_similarity(left: Any, right: Any) -> float:
    try:
        import numpy as np

        dot = float(np.dot(left, right))
        left_norm = float(np.linalg.norm(left))
        right_norm = float(np.linalg.norm(right))
        if left_norm <= 0 or right_norm <= 0:
            return 0.0
        return dot / (left_norm * right_norm)
    except Exception:  # noqa: BLE001
        return 0.0
