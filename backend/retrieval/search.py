"""Hybrid retrieval: fusion logic shared by the offline reference searcher and the production KnowledgeBase.

    vector similarity (cosine over unit vectors)  +  keyword BM25  ->  weighted reciprocal-rank fusion
    -> jurisdiction / status factors -> de-duplication of identical texts (Federal vs Punjab copies)

`fuse()` is generic over the candidate key (row index offline, chunk_id in production) so there is ONE implementation.
`HybridSearcher` is the in-memory reference used by the evaluation harness; `retrieval.kb.KnowledgeBase` is the production
path (pgvector in Postgres + local BM25).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Hashable

import numpy as np

from .lexical import LexicalIndex

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def slug(model: str) -> str:
    return model.replace("/", "__")


class QueryEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5", prefix: str = BGE_QUERY_PREFIX):
        from fastembed import TextEmbedding
        self.model_name, self.prefix = model, prefix
        self.model = TextEmbedding(model_name=model)

    def embed(self, texts: list[str], use_prefix: bool = True) -> np.ndarray:
        pre = self.prefix if use_prefix else ""
        v = np.array(list(self.model.embed([pre + t for t in texts])), dtype=np.float32)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


@dataclass
class Params:
    w_vec: float = 1.0
    w_lex: float = 1.0
    rrf_k: int = 60
    depth: int = 50               # candidates taken from each retriever
    use_prefix: bool = True
    juris_boost: float = 1.15     # chunk belongs to the user's jurisdiction
    juris_penalty: float = 0.70   # chunk belongs to a different province / ICT
    repealed_factor: float = 1.0  # < 1 to demote repealed laws (kept visible: users may ask about them)
    dedupe: bool = True


@dataclass
class Hit:
    key: Hashable
    score: float
    cos: float = 0.0
    bm25: float = 0.0
    sources: tuple = field(default_factory=tuple)

    @property
    def idx(self):          # offline code addresses candidates by row index
        return self.key


def jurisdiction_factor(chunk_jur: str, applies_to: set[str], repealed: bool, user_jur: str | None, p: Params) -> float:
    f = 1.0
    if user_jur:
        if user_jur in applies_to:
            f *= p.juris_boost if chunk_jur == user_jur else 1.0
        elif "Federal" not in applies_to:
            f *= p.juris_penalty
    if repealed:
        f *= p.repealed_factor
    return f


def fuse(vec: list[tuple[Hashable, float]], lex: list[tuple[Hashable, float]], p: Params,
         factor: Callable[[Hashable], float], text_hash: Callable[[Hashable], str], k: int) -> list[Hit]:
    """Weighted reciprocal-rank fusion of the two ranked candidate lists."""
    fused: dict[Hashable, Hit] = {}
    if p.w_vec > 0:
        for rank, (key, cos) in enumerate(vec, start=1):
            h = fused.setdefault(key, Hit(key, 0.0))
            h.score += p.w_vec / (p.rrf_k + rank)
            h.cos = cos
            h.sources += ("vec",)
    if p.w_lex > 0:
        for rank, (key, s) in enumerate(lex, start=1):
            h = fused.setdefault(key, Hit(key, 0.0))
            h.score += p.w_lex / (p.rrf_k + rank)
            h.bm25 = s
            h.sources += ("lex",)
    hits = list(fused.values())
    for h in hits:
        h.score *= factor(h.key)
    hits.sort(key=lambda h: -h.score)
    if p.dedupe:
        seen, out = set(), []
        for h in hits:
            th = text_hash(h.key)
            if th in seen:
                continue
            seen.add(th)
            out.append(h)
        hits = out
    return hits[:k]


class HybridSearcher:
    """In-memory reference implementation (numpy + SQLite FTS5) used to evaluate and tune."""

    def __init__(self, chunks: list[dict], model: str = "BAAI/bge-small-en-v1.5", embedder: QueryEmbedder | None = None):
        from ingest.config import DATA_DIR      # offline tooling only: the deployed app must not depend on the pipeline package
        self.chunks = chunks
        self.emb = np.load(DATA_DIR / "index" / slug(model) / "embeddings.npy", mmap_mode="r")
        assert self.emb.shape[0] == len(chunks), "embeddings and chunks are out of sync"
        self.is_toc = [c["unit_type"] == "toc" for c in chunks]
        self.lex = LexicalIndex([(i, c["header"], c["text"]) for i, c in enumerate(chunks) if c["unit_type"] != "toc"])
        self.embedder = embedder or QueryEmbedder(model)
        self.applies = [set(c["applies_to"]) | {c["jurisdiction"]} for c in chunks]
        self.hashes = [c["chunk_hash"] for c in chunks]
        self.repealed = [c["legal_status"] == "repealed" for c in chunks]

    def vector(self, qvec: np.ndarray, depth: int) -> list[tuple[int, float]]:
        sims = np.asarray(self.emb) @ qvec
        top = np.argpartition(-sims, depth)[:depth]
        top = top[np.argsort(-sims[top])]
        return [(int(i), float(sims[i])) for i in top if not self.is_toc[int(i)]]

    def search(self, query: str, jur: str | None = None, k: int = 20, p: Params | None = None,
               qvec: np.ndarray | None = None) -> list[Hit]:
        p = p or Params()
        vec, lex = [], []
        qv = None
        if p.w_vec > 0:
            qv = qvec if qvec is not None else self.embedder.embed([query], p.use_prefix)[0]
            vec = self.vector(qv, p.depth)
        if p.w_lex > 0:
            lex = self.lex.search(query, p.depth)
        hits = fuse(vec, lex, p,
                    lambda i: jurisdiction_factor(self.chunks[i]["jurisdiction"], self.applies[i], self.repealed[i], jur, p),
                    lambda i: self.hashes[i], k)
        if qv is not None:
            for h in hits:                              # keyword-only candidates still get a cosine (used for confidence)
                if h.cos == 0.0:
                    h.cos = float(self.emb[h.key] @ qv)
        return hits
