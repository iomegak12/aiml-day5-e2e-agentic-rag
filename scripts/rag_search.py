"""
rag_search.py - Reusable retrieval functions for the NetCore KB vector databases (Chroma server).

Three retrieval modes over one domain database ("networking" or "meetings"):
  similarity_search(query, domain)  -> dense vector search (OpenAI embeddings)   score = relevance 0-1
  keyword_search(query, domain)     -> BM25 lexical search over the stored chunks  score = BM25
  hybrid_search(query, domain)      -> BM25 + vector fused with Reciprocal Rank Fusion (EnsembleRetriever)

Each returns [(Document, score), ...] best first. For LCEL chains use:
  get_retriever(mode, domain, k, filter)  -> a LangChain BaseRetriever (KBRetriever)
  format_docs(docs)                       -> numbered, citable context string for the prompt

Example:
  from rag_search import hybrid_search, get_retriever, format_docs
  for doc, score in hybrid_search("MTG-JOIN-1007 firewall", "meetings"):
      print(score, doc.metadata["kb_id"])
"""

from __future__ import annotations

import json
import re
import warnings
from functools import lru_cache
from typing import Literal

warnings.filterwarnings("ignore", category=DeprecationWarning)  # langchain-community sunset notice

from langchain_chroma import Chroma  # noqa: E402
from langchain_classic.retrievers import EnsembleRetriever  # noqa: E402
from langchain_community.retrievers import BM25Retriever  # noqa: E402
from langchain_core.callbacks import CallbackManagerForRetrieverRun  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_core.retrievers import BaseRetriever  # noqa: E402
from langchain_openai import OpenAIEmbeddings  # noqa: E402
from populate_vector_dbs import DOMAINS, Config, http_client, load_config  # noqa: E402

DEFAULT_K = 4
DEFAULT_WEIGHTS = (0.5, 0.5)  # (BM25, vector)
RRF_C = 60  # Reciprocal Rank Fusion constant (EnsembleRetriever default)
SearchMode = Literal["similarity", "keyword", "hybrid"]

# =============================================================================
# Connections (cached - created once per process)
# =============================================================================


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Settings from .env (Chroma host/port/databases, models, chunking)."""
    return load_config()


@lru_cache(maxsize=1)
def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=get_config().embedding_model)


@lru_cache(maxsize=None)
def get_vector_store(domain: str) -> Chroma:
    """LangChain Chroma vector store bound to the domain's database on the Chroma server."""
    if domain not in DOMAINS:
        raise ValueError(f"domain must be one of {DOMAINS}, got {domain!r}")
    cfg = get_config()
    return Chroma(client=http_client(cfg, cfg.databases[domain]), collection_name=cfg.collection,
                  embedding_function=_embeddings(), create_collection_if_not_exists=False)


def _copy(doc: Document, **extra) -> Document:
    """Return a copy with extra metadata (never mutate cached documents)."""
    return Document(id=doc.id, page_content=doc.page_content, metadata={**doc.metadata, **extra})


# =============================================================================
# 1. Similarity search (dense vectors)
# =============================================================================


def similarity_search(query: str, domain: str, k: int = DEFAULT_K,
                      filter: dict | None = None) -> list[tuple[Document, float]]:
    """Vector search. Score = relevance (0-1, higher is better); raw L2 distance kept in metadata."""
    store = get_vector_store(domain)
    to_relevance = store._select_relevance_score_fn()  # L2 distance -> 0-1 relevance (LangChain's mapping)
    return [(_copy(d, distance=round(dist, 4), score=round(to_relevance(dist), 4), search_type="similarity"),
             round(to_relevance(dist), 4))
            for d, dist in store.similarity_search_with_score(query, k=k, filter=filter)]


# =============================================================================
# 2. Keyword search (BM25)
# =============================================================================


def tokenize(text: str) -> list[str]:
    """Lower-case tokens that keep codes such as 'ncs-sla-2001' or 'kb-net-1003' intact."""
    return re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", text.lower())


@lru_cache(maxsize=32)
def _bm25(domain: str, filter_key: str, k: int) -> BM25Retriever:
    """BM25 index over all chunks of a domain (optionally pre-filtered by metadata). Built client-side."""
    where = json.loads(filter_key) or None
    data = get_vector_store(domain).get(where=where, include=["documents", "metadatas"])
    docs = [Document(id=i, page_content=t, metadata=m)
            for i, t, m in zip(data["ids"], data["documents"], data["metadatas"])]
    if not docs:
        raise ValueError(f"No chunks in '{domain}' match filter {where}")
    return BM25Retriever.from_documents(docs, preprocess_func=tokenize, k=k)


def keyword_search(query: str, domain: str, k: int = DEFAULT_K,
                   filter: dict | None = None) -> list[tuple[Document, float]]:
    """BM25 lexical search. Score = BM25 (unbounded, higher is better); zero-score chunks are dropped."""
    retriever = _bm25(domain, json.dumps(filter or {}, sort_keys=True), k)
    scores = retriever.vectorizer.get_scores(tokenize(query))
    ranked = sorted(zip(retriever.docs, scores), key=lambda x: x[1], reverse=True)[:k]
    return [(_copy(d, score=round(float(s), 4), search_type="keyword"), round(float(s), 4))
            for d, s in ranked if s > 0]


# =============================================================================
# 3. Hybrid search (BM25 + vector, Reciprocal Rank Fusion)
# =============================================================================


def hybrid_search(query: str, domain: str, k: int = DEFAULT_K, weights: tuple[float, float] = DEFAULT_WEIGHTS,
                  filter: dict | None = None) -> list[tuple[Document, float]]:
    """EnsembleRetriever over BM25 + vector. Score = RRF = sum(weight / (60 + rank)); ranks kept in metadata."""
    bm25 = _bm25(domain, json.dumps(filter or {}, sort_keys=True), k)
    vector = get_vector_store(domain).as_retriever(search_kwargs={"k": k, "filter": filter})
    ensemble = EnsembleRetriever(retrievers=[bm25, vector], weights=list(weights), c=RRF_C)
    fused = ensemble.invoke(query)[:k]

    # Ranks in the individual retrievers - lets students see *why* a chunk was fused to the top
    bm25_rank = {d.id: r for r, d in enumerate(bm25.invoke(query), start=1)}
    vec_rank = {d.id: r for r, d in enumerate(vector.invoke(query), start=1)}
    results = []
    for d in fused:
        rrf = round(sum(w / (RRF_C + ranks[d.id]) for w, ranks in zip(weights, (bm25_rank, vec_rank))
                        if d.id in ranks), 5)
        results.append((_copy(d, score=rrf, search_type="hybrid", bm25_rank=bm25_rank.get(d.id, 0),
                              vector_rank=vec_rank.get(d.id, 0)), rrf))
    return results


SEARCH_FUNCTIONS = {"similarity": similarity_search, "keyword": keyword_search, "hybrid": hybrid_search}


def search(query: str, domain: str, mode: SearchMode = "hybrid", k: int = DEFAULT_K,
           filter: dict | None = None) -> list[tuple[Document, float]]:
    """Dispatch to similarity_search / keyword_search / hybrid_search."""
    return SEARCH_FUNCTIONS[mode](query, domain, k=k, filter=filter)


# =============================================================================
# 4. LangChain retriever (for LCEL chains)
# =============================================================================


class KBRetriever(BaseRetriever):
    """LangChain retriever over one NetCore domain database. Docs carry 'score' and 'search_type' metadata."""

    domain: str
    mode: SearchMode = "hybrid"
    k: int = DEFAULT_K
    filter: dict | None = None

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return [doc for doc, _ in search(query, self.domain, self.mode, self.k, self.filter)]


def get_retriever(mode: SearchMode = "hybrid", domain: str = "networking", k: int = DEFAULT_K,
                  filter: dict | None = None) -> KBRetriever:
    """Factory: get_retriever('similarity', 'meetings', filter={'status': 'current'})."""
    if mode not in SEARCH_FUNCTIONS:
        raise ValueError(f"mode must be one of {list(SEARCH_FUNCTIONS)}, got {mode!r}")
    return KBRetriever(domain=domain, mode=mode, k=k, filter=filter)


# =============================================================================
# 5. Context formatting & display
# =============================================================================


def location(meta: dict) -> str:
    """Human-readable, citable location: 'Table 2, p.3' / 'Code block 1, section X' / 'p.2' / 'chunk 4'."""
    parts = []
    if meta.get("content_type") in ("table", "code"):
        parts.append(f"{'Table' if meta['content_type'] == 'table' else 'Code block'} {meta.get('item_index', '')}")
    if meta.get("page"):
        parts.append(f"p.{meta['page']}")
    elif meta.get("section"):
        parts.append(f"section '{meta['section']}'")
    if not parts:
        parts.append(f"chunk {meta.get('chunk_index', '?')}")
    return ", ".join(parts)


def format_docs(docs: list[Document]) -> str:
    """Numbered source blocks with everything the LLM needs to cite and to judge freshness."""
    blocks = []
    for n, d in enumerate(docs, start=1):
        m = d.metadata
        status = (f"SUPERSEDED by {m.get('superseded_by')}" if m.get("status") == "superseded"
                  else m.get("status", "current"))
        header = (f"[Source {n}] {m.get('kb_id')} | {m.get('title')} | {m.get('product')} {m.get('version')} "
                  f"| status: {status} | location: {location(m)}")
        blocks.append(f"{header}\n{d.page_content.strip()}")
    return "\n\n---\n\n".join(blocks)


def show_results(results: list[tuple[Document, float]] | list[Document], title: str = "") -> None:
    """Pretty-print search results (works in terminals and Jupyter via rich)."""
    from rich.console import Console
    from rich.markup import escape
    from rich.table import Table

    rows = [(r if isinstance(r, tuple) else (r, r.metadata.get("score", 0.0))) for r in results]
    t = Table(title=escape(title), title_justify="left", header_style="bold cyan", expand=True)
    for col, kw in (("#", {"justify": "right", "width": 2}), ("Score", {"justify": "right", "width": 8}),
                    ("KB ID", {"width": 11, "no_wrap": True}), ("Type", {"width": 5}),
                    ("Status", {"width": 10}), ("Location", {"width": 16}), ("Snippet", {"ratio": 1})):
        t.add_column(col, **kw)
    for rank, (doc, score) in enumerate(rows, start=1):
        m = doc.metadata
        text = doc.page_content.split("\nDescription: ", 1)[-1]  # table/code chunks: show the description
        text = " ".join(text.split())
        status = "[red]superseded[/red]" if m.get("status") == "superseded" else m.get("status", "")
        t.add_row(str(rank), f"{score:.4f}", m.get("kb_id", ""), m.get("content_type", ""), status,
                  escape(location(m)), escape(text[:120] + ("..." if len(text) > 120 else "")))
    Console().print(t)


if __name__ == "__main__":  # quick smoke test: uv run scripts/rag_search.py
    for dom, q in (("networking", "NCS-SLA-2001 escalation to Sev1"), ("meetings", "MTG-JOIN-1007 firewall ports")):
        for mode in SEARCH_FUNCTIONS:
            show_results(search(q, dom, mode), f"{dom} | {mode} | {q}")
