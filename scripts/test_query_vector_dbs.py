"""
test_query_vector_dbs.py - Explore and query the Chroma vector databases built by populate_vector_dbs.py.

Sections:
  1. Connection & database info   (heartbeat, server version, tenant, databases, collections, counts, metadata)
  2. Similarity search            (rank, raw L2 distance, normalised relevance score)
  3. Keyword search               (Chroma $contains - exact, unranked  vs  BM25 - ranked lexical)
  4. Metadata filtering           (status=current, content_type, kb_id / version)
  5. Hybrid search                (EnsembleRetriever: BM25 + vector, Reciprocal Rank Fusion)
  6. Cross-domain query           (same question against both databases)

Usage (from the project root; or `make test-query` / `make query Q="..." D=meetings`):
  uv run scripts/test_query_vector_dbs.py                                    # all demos
  uv run scripts/test_query_vector_dbs.py --query "MTG-JOIN-1007" --domain meetings
"""

from __future__ import annotations

import argparse
import re
import warnings

warnings.filterwarnings("ignore")  # langchain-community sunset notice etc.

import chromadb  # noqa: E402
from langchain_chroma import Chroma  # noqa: E402
from langchain_classic.retrievers import EnsembleRetriever  # noqa: E402
from langchain_community.retrievers import BM25Retriever  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_openai import OpenAIEmbeddings  # noqa: E402
from populate_vector_dbs import DOMAINS, Config, chroma_settings, http_client, load_config  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.markup import escape  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

K = 3
RRF_C = 60  # EnsembleRetriever's default rank constant
console = Console()

# Curated demo queries per domain
SIMILARITY_QUERIES = {
    "networking": ["How long before an SLA breach escalates to Sev1?",
                   "What are the latency and jitter thresholds for the Voice SLA class?"],
    "meetings": ["How long are cloud meeting recordings kept?",
                 "How do I configure a hunt group for a support line?"],
}
KEYWORDS = {"networking": "NCS-BFD-3004", "meetings": "MTG-JOIN-1007"}
HYBRID_QUERIES = {"networking": "NCS-SLA-2001 escalation to Sev2",
                  "meetings": "MTG-MED-4102 packet loss during meetings"}
CROSS_DOMAIN_QUERY = "Which ports and QoS markings does NetCore Meet media traffic need on the network?"


# =============================================================================
# Helpers
# =============================================================================


class KB:
    """One domain = one Chroma database: holds the LangChain vector store and a lazily built BM25 index."""

    def __init__(self, domain: str, cfg: Config, embeddings: OpenAIEmbeddings):
        self.domain, self.database = domain, cfg.databases[domain]
        self.client = http_client(cfg, self.database)
        self.collection = self.client.get_collection(cfg.collection)
        self.store = Chroma(client=self.client, collection_name=cfg.collection, embedding_function=embeddings)
        self._bm25: BM25Retriever | None = None

    def all_documents(self) -> list[Document]:
        data = self.collection.get(include=["documents", "metadatas"])
        return [Document(id=i, page_content=t, metadata=m)
                for i, t, m in zip(data["ids"], data["documents"], data["metadatas"])]

    @property
    def bm25(self) -> BM25Retriever:
        if self._bm25 is None:  # BM25 runs client-side over every chunk pulled from Chroma
            self._bm25 = BM25Retriever.from_documents(self.all_documents(), preprocess_func=tokenize, k=K)
        return self._bm25


def tokenize(text: str) -> list[str]:
    """Lower-case tokens that keep codes such as 'ncs-sla-2001' or 'kb-net-1003' intact."""
    return re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", text.lower())


def location(meta: dict) -> str:
    if meta.get("page"):
        return f"p.{meta['page']}"
    return (meta.get("section") or "-")[:22]


def snippet(text: str, n: int = 110) -> str:
    """Table/code chunks start with a reference header - show their description instead."""
    if "\nDescription: " in text:
        text = text.split("\nDescription: ", 1)[1]
    text = " ".join(text.split())
    return escape(text[:n] + ("..." if len(text) > n else ""))


def result_table(title: str, rows: list[dict], score_cols: list[str]) -> Table:
    t = Table(title=escape(title), title_justify="left", show_lines=False, header_style="bold cyan", expand=True)
    t.add_column("#", justify="right", width=2)
    for col in score_cols:
        t.add_column(col, justify="right", width=9)
    for col, width in (("KB ID", 11), ("Type", 5), ("Status", 10), ("Loc", 9)):
        t.add_column(col, width=width, no_wrap=True)
    t.add_column("Snippet", ratio=1)
    for rank, r in enumerate(rows, start=1):
        m = r["doc"].metadata
        status = f"[red]{m.get('status')}[/red]" if m.get("status") == "superseded" else m.get("status", "")
        t.add_row(str(rank), *[r[c] for c in score_cols], m.get("kb_id", ""), m.get("content_type", ""),
                  status, location(m), snippet(r["doc"].page_content))
    if not rows:
        t.add_row("-", *["-"] * len(score_cols), "no results", "", "", "", "")
    return t


def section(title: str, subtitle: str) -> None:
    console.print()
    console.print(Panel(f"[bold]{escape(title)}[/bold]\n[dim]{escape(subtitle)}[/dim]", border_style="blue"))


# =============================================================================
# Search primitives
# =============================================================================


def similarity(kb: KB, query: str, flt: dict | None = None) -> list[dict]:
    """Distance (L2, lower = closer) and LangChain's relevance score (0-1, higher = better)."""
    with_dist = kb.store.similarity_search_with_score(query, k=K, filter=flt)
    relevance = {d.id: s for d, s in kb.store.similarity_search_with_relevance_scores(query, k=K, filter=flt)}
    return [{"doc": d, "Distance": f"{dist:.4f}", "Relevance": f"{relevance.get(d.id, 0):.4f}"}
            for d, dist in with_dist]


def contains(kb: KB, term: str) -> tuple[int, list[dict]]:
    """Chroma native full-text filter: exact, case-sensitive substring match, no ranking."""
    data = kb.collection.get(where_document={"$contains": term}, include=["documents", "metadatas"])
    docs = [Document(id=i, page_content=t, metadata=m)
            for i, t, m in zip(data["ids"], data["documents"], data["metadatas"])]
    return len(docs), [{"doc": d} for d in docs[:K]]


def bm25(kb: KB, query: str) -> list[dict]:
    """BM25 (Okapi) lexical ranking; scores read from the underlying rank_bm25 index."""
    retriever = kb.bm25
    scores = retriever.vectorizer.get_scores(tokenize(query))
    ranked = sorted(zip(retriever.docs, scores), key=lambda x: x[1], reverse=True)[:K]
    return [{"doc": d, "BM25": f"{s:.3f}"} for d, s in ranked if s > 0]


def hybrid(kb: KB, query: str) -> list[dict]:
    """EnsembleRetriever fuses BM25 + vector rankings with weighted Reciprocal Rank Fusion."""
    vector = kb.store.as_retriever(search_kwargs={"k": K})
    weights = [0.5, 0.5]
    ensemble = EnsembleRetriever(retrievers=[kb.bm25, vector], weights=weights, c=RRF_C, id_key=None)
    fused = ensemble.invoke(query)[:K]

    # For teaching: show each result's rank in the individual retrievers and its RRF score
    bm25_rank = {d.id: r for r, d in enumerate(kb.bm25.invoke(query), start=1)}
    vec_rank = {d.id: r for r, d in enumerate(vector.invoke(query), start=1)}
    rows = []
    for d in fused:
        rrf = sum(w / (RRF_C + rk[d.id]) for w, rk in zip(weights, (bm25_rank, vec_rank)) if d.id in rk)
        rows.append({"doc": d, "BM25 #": str(bm25_rank.get(d.id, "-")), "Vector #": str(vec_rank.get(d.id, "-")),
                     "RRF": f"{rrf:.5f}"})
    return rows


# =============================================================================
# Demo sections
# =============================================================================


def show_info(cfg: Config, kbs: dict[str, KB]) -> None:
    section("1. Connection & Database Info", "Chroma server -> tenant -> databases -> collections")
    any_client = next(iter(kbs.values())).client
    admin = chromadb.AdminClient(chroma_settings(cfg))
    info = Table(show_header=False, box=None)
    info.add_row("Server", f"http://{cfg.chroma_host}:{cfg.chroma_port}")
    info.add_row("Heartbeat (ns)", str(any_client.heartbeat()))
    info.add_row("Server API version", any_client.get_version())
    info.add_row("Client (chromadb) version", chromadb.__version__)
    info.add_row("Tenant", cfg.chroma_tenant)
    info.add_row("Databases", ", ".join(d["name"] for d in admin.list_databases(tenant=cfg.chroma_tenant)))
    info.add_row("Embedding model", cfg.embedding_model)
    console.print(info)

    t = Table(title="Configured domain databases", title_justify="left", header_style="bold cyan")
    for col in ("Domain", "Database", "Collections", "Chunks", "Text/Table/Code", "Articles", "Distance",
                "Metadata keys"):
        t.add_column(col)
    for domain, kb in kbs.items():
        metas = kb.collection.get(include=["metadatas"])["metadatas"]
        by_type = {ct: sum(m["content_type"] == ct for m in metas) for ct in ("text", "table", "code")}
        space = (kb.collection.configuration or {}).get("hnsw", {}) or {}
        t.add_row(domain, kb.database, ", ".join(c.name for c in kb.client.list_collections()),
                  str(kb.collection.count()), "/".join(str(v) for v in by_type.values()),
                  str(len({m["kb_id"] for m in metas})), str(space.get("space", "l2")),
                  ", ".join(sorted({k for m in metas for k in m})))
    console.print(t)


def show_similarity(kbs: dict[str, KB]) -> None:
    section("2. Similarity Search", "Embedding similarity: distance (L2, lower = closer) and relevance (0-1, higher = better)")
    for domain, kb in kbs.items():
        for q in SIMILARITY_QUERIES[domain]:
            console.print(result_table(f"[{domain}] {q}", similarity(kb, q), ["Distance", "Relevance"]))


def show_keyword(kbs: dict[str, KB]) -> None:
    section("3. Keyword Search", "Chroma $contains (exact, server-side, unranked)  vs  BM25 (lexical, ranked)")
    for domain, kb in kbs.items():
        term = KEYWORDS[domain]
        total, rows = contains(kb, term)
        console.print(result_table(f"[{domain}] $contains '{term}' -> {total} matching chunks (first {K}, unranked)",
                                   rows, []))
        console.print(result_table(f"[{domain}] BM25 '{term}'", bm25(kb, term), ["BM25"]))
        lower_total, _ = contains(kb, term.lower())
        console.print(f"[dim]  $contains is case-sensitive: '{term.lower()}' -> {lower_total} chunks; "
                      f"BM25 here lower-cases tokens, so case does not matter[/dim]")


def show_filters(kbs: dict[str, KB]) -> None:
    section("4. Metadata Filtering", "Same vector search, narrowed by metadata (where clause)")
    scenarios = [
        ("networking", "How long before an SLA breach is declared?", None, "no filter"),
        ("networking", "How long before an SLA breach is declared?", {"status": "current"}, "status = current"),
        ("meetings", "recording retention period and legal hold", {"content_type": {"$in": ["table", "code"]}},
         "content_type in [table, code]"),
        ("networking", "SLA breach notification", {"version": "4.2"}, "version = 4.2"),
        ("meetings", "firewall ports required for media", {"kb_id": "KB-MTG-2007"}, "kb_id = KB-MTG-2007"),
    ]
    for domain, q, flt, label in scenarios:
        if domain in kbs:
            console.print(result_table(f"[{domain}] {q}  |  filter: {label}", similarity(kbs[domain], q, flt),
                                       ["Distance", "Relevance"]))


def show_hybrid(kbs: dict[str, KB]) -> None:
    section("5. Hybrid Search", f"EnsembleRetriever: BM25 + vector, weights 0.5/0.5, RRF score = sum w/({RRF_C}+rank)")
    for domain, kb in kbs.items():
        q = HYBRID_QUERIES[domain]
        console.print(result_table(f"[{domain}] {q}", hybrid(kb, q), ["BM25 #", "Vector #", "RRF"]))


def show_cross_domain(kbs: dict[str, KB]) -> None:
    section("6. Cross-Domain Query", "The same question against each domain database")
    for domain, kb in kbs.items():
        console.print(result_table(f"[{domain}] {CROSS_DOMAIN_QUERY}", similarity(kb, CROSS_DOMAIN_QUERY),
                                   ["Distance", "Relevance"]))


def ad_hoc(query: str, kbs: dict[str, KB]) -> None:
    section(f"Ad-hoc query: {query}", "similarity, BM25 and hybrid results per domain")
    for domain, kb in kbs.items():
        console.print(result_table(f"[{domain}] similarity", similarity(kb, query), ["Distance", "Relevance"]))
        console.print(result_table(f"[{domain}] BM25", bm25(kb, query), ["BM25"]))
        console.print(result_table(f"[{domain}] hybrid", hybrid(kb, query), ["BM25 #", "Vector #", "RRF"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore and query the Chroma KB databases.")
    parser.add_argument("--query", help="Run an ad-hoc query instead of the built-in demos")
    parser.add_argument("--domain", choices=[*DOMAINS, "all"], default="all")
    args = parser.parse_args()

    cfg = load_config()
    embeddings = OpenAIEmbeddings(model=cfg.embedding_model)
    domains = list(DOMAINS) if args.domain == "all" else [args.domain]
    try:
        kbs = {d: KB(d, cfg, embeddings) for d in domains}
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Cannot open the Chroma databases ({exc}). Run `make chroma-up` and `make populate`.")

    if args.query:
        ad_hoc(args.query, kbs)
        return
    show_info(cfg, kbs)
    show_similarity(kbs)
    show_keyword(kbs)
    show_filters(kbs)
    show_hybrid(kbs)
    if len(kbs) > 1:
        show_cross_domain(kbs)


if __name__ == "__main__":
    main()
