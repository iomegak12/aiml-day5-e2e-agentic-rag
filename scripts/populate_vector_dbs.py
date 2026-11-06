"""
populate_vector_dbs.py - Pre-RAG data engineering pipeline.

  KB files (PDF / HTML / MD)
    -> Data Readers (LangChain community loaders)
    -> Metadata (embedded file metadata, manifest.json fallback, product family)
    -> Chunking (RecursiveCharacterTextSplitter, size-based)
    -> Table / code descriptions (LLM) as separate chunks with document/page/table references
    -> Embeddings (OpenAI)
    -> Chroma server: one database per domain, one collection per database

Usage (from the project root; or use the Makefile targets):
  uv run scripts/populate_vector_dbs.py                       # both domains
  uv run scripts/populate_vector_dbs.py --domain networking   # one domain
  uv run scripts/populate_vector_dbs.py --stats               # print what is stored

All settings come from .env (see .env.example).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("UNSTRUCTURED_DISABLE_NOTICE", "1")
warnings.filterwarnings("ignore", category=DeprecationWarning)  # langchain-community sunset notice

import chromadb  # noqa: E402
import pdfplumber  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from chromadb.config import Settings  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from langchain_chroma import Chroma  # noqa: E402
from langchain_community.document_loaders import (  # noqa: E402
    PyPDFLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
)
from langchain_core.documents import Document  # noqa: E402
from langchain_core.output_parsers import StrOutputParser  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ("networking", "meetings")
PRODUCT_FAMILY = {"networking": "Networking", "meetings": "Collaboration"}
LIST_FIELDS = ("error_codes", "related", "tags")
MAX_ITEM_CHARS = 6000  # cap raw table/code text stored in a description chunk

# =============================================================================
# 1. Configuration (.env)
# =============================================================================


@dataclass
class Config:
    kb_data_dir: Path
    chroma_host: str
    chroma_port: int
    chroma_tenant: str
    databases: dict[str, str]
    collection: str
    chunk_size: int
    chunk_overlap: int
    describe_concurrency: int
    chat_model: str
    embedding_model: str


def load_config() -> Config:
    load_dotenv(PROJECT_ROOT / ".env")
    env = os.environ.get
    data_dir = Path(env("KB_DATA_DIR", "data/raw"))
    return Config(
        kb_data_dir=data_dir if data_dir.is_absolute() else PROJECT_ROOT / data_dir,
        chroma_host=env("CHROMA_HOST", "localhost"),
        chroma_port=int(env("CHROMA_PORT", "8000")),
        chroma_tenant=env("CHROMA_TENANT", "default_tenant"),
        databases={"networking": env("CHROMA_DB_NETWORKING", "networking_kb"),
                   "meetings": env("CHROMA_DB_MEETINGS", "meetings_kb")},
        collection=env("CHROMA_COLLECTION", "kb_articles"),
        chunk_size=int(env("CHUNK_SIZE", "3000")),
        chunk_overlap=int(env("CHUNK_OVERLAP", "200")),
        describe_concurrency=int(env("DESCRIBE_CONCURRENCY", "8")),
        chat_model=os.environ["OPENAI_MODEL"],
        embedding_model=os.environ["OPENAI_EMBEDDING_MODEL"],
    )


# =============================================================================
# 2. Metadata - embedded file metadata first, manifest.json as fallback
# =============================================================================


def _split_list(value: str, sep: str) -> list[str]:
    return [v.strip() for v in value.split(sep) if v.strip()]


def md_frontmatter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, raw = line.partition(":")
        try:
            meta[key.strip()] = json.loads(raw.strip())
        except json.JSONDecodeError:
            meta[key.strip()] = raw.strip().strip('"')
    return meta


def html_meta(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    meta = {m["name"]: m.get("content", "") for m in soup.find_all("meta", attrs={"name": True})}
    for f in LIST_FIELDS:
        if f in meta:
            meta[f] = _split_list(meta[f], ",")
    return meta


def pdf_meta(pdf_doc_metadata: dict) -> dict:
    """PDF keywords look like 'kb_id=KB-NET-1001; ...; related=KB-NET-1002|KB-NET-1003'."""
    meta = {}
    for pair in pdf_doc_metadata.get("keywords", "").split(";"):
        key, sep, value = pair.partition("=")
        if sep:
            meta[key.strip()] = value.strip()
    for f in LIST_FIELDS:
        if f in meta:
            meta[f] = _split_list(meta[f], "|")
    if title := pdf_doc_metadata.get("title"):
        meta["title"] = title.split(": ", 1)[-1]  # "KB-NET-1001: Title" -> "Title"
    if author := pdf_doc_metadata.get("author"):
        meta["author"] = author
    return meta


def build_metadata(domain: str, path: Path, file_meta: dict, manifest: dict[str, dict]) -> dict:
    merged = {**manifest.get(path.name, {}), **{k: v for k, v in file_meta.items() if v not in (None, "")}}
    merged.pop("file", None)
    merged.pop("format", None)
    merged.update(domain=domain, product_family=PRODUCT_FAMILY[domain], source_file=path.name,
                  file_format=path.suffix.lstrip("."))
    # Chroma metadata values must be scalars -> join lists
    return {k: ", ".join(v) if isinstance(v, list) else v for k, v in merged.items()}


def load_manifest(domain_dir: Path) -> dict[str, dict]:
    path = domain_dir / "manifest.json"
    if not path.exists():
        return {}
    return {a["file"]: a for a in json.loads(path.read_text(encoding="utf-8"))["articles"]}


# =============================================================================
# 3. Data readers - LangChain community loaders
# =============================================================================


def read_file(path: Path) -> tuple[list[Document], dict]:
    """Return (page/document list, embedded file metadata)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = PyPDFLoader(str(path)).load()  # one Document per page; metadata includes PDF doc-info
        file_meta = pdf_meta(pages[0].metadata) if pages else {}
        for p in pages:
            p.metadata = {"page": p.metadata.get("page", 0) + 1}  # keep only a 1-based page number
        return pages, file_meta
    if suffix == ".html":
        docs = UnstructuredHTMLLoader(str(path), mode="single").load()
        return [Document(page_content=docs[0].page_content)], html_meta(path)
    if suffix == ".md":
        docs = UnstructuredMarkdownLoader(str(path), mode="single").load()
        text = docs[0].page_content
        if text.startswith("kb_id:"):  # frontmatter is rendered as the first paragraph - drop it
            text = text.split("\n\n", 1)[-1]
        return [Document(page_content=text)], md_frontmatter(path)
    raise ValueError(f"Unsupported file type: {path}")


# =============================================================================
# 4. Table / code extraction (per format) - with document, page and section references
# =============================================================================


@dataclass
class Item:
    kind: str  # table | code
    index: int  # 1-based, per kind, per document
    content: str  # table as Markdown, or code text
    page: int | None = None
    section: str = ""
    caption: str = ""
    language: str = ""


def _rows_to_markdown(rows: list[list[str]]) -> str:
    clean = [[(c or "").replace("\n", " ").replace("|", "/").strip() for c in r] for r in rows if any(r)]
    if not clean:
        return ""
    width = max(len(r) for r in clean)
    clean = [r + [""] * (width - len(r)) for r in clean]
    lines = ["| " + " | ".join(clean[0]) + " |", "|" + "---|" * width]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in clean[1:]])


def extract_md(path: Path) -> list[Item]:
    items, counters, section = [], Counter(), ""
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip()
        if line.startswith("```"):
            lang, body, i = line[3:].strip(), [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            counters["code"] += 1
            items.append(Item("code", counters["code"], "\n".join(body), section=section, language=lang))
        elif line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1]):
            start = i
            while i < len(lines) and lines[i].startswith("|"):
                i += 1
            prev = next((lines[j] for j in range(start - 1, -1, -1) if lines[j].strip()), "")
            caption = prev.strip("*_ ") if prev.startswith(("*", "_")) else ""
            counters["table"] += 1
            items.append(Item("table", counters["table"], "\n".join(lines[start:i]), section=section, caption=caption))
            continue
        i += 1
    return items


def extract_html(path: Path) -> list[Item]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    items, counters = [], Counter()
    for el in soup.find_all(["table", "pre"]):
        heading = el.find_previous("h2")
        section = heading.get_text(strip=True) if heading else ""
        if el.name == "table":
            rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in el.find_all("tr")]
            caption = el.caption.get_text(strip=True) if el.caption else ""
            counters["table"] += 1
            items.append(Item("table", counters["table"], _rows_to_markdown(rows), section=section, caption=caption))
        else:
            code = el.find("code")
            lang = next((c.removeprefix("language-") for c in (code.get("class") or []) if c.startswith("language-")),
                        "") if code else ""
            counters["code"] += 1
            items.append(Item("code", counters["code"], el.get_text(), section=section, language=lang))
    return items


def extract_pdf(path: Path) -> list[Item]:
    items, counters = [], Counter()
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            # Tables: pdfplumber's ruling-line detection; caption = text just above the table
            for table in page.find_tables():
                rows = table.extract()
                top = table.bbox[1]
                above = page.within_bbox((0, max(0, top - 16), page.width, top)).extract_text() or ""
                counters["table"] += 1
                items.append(Item("table", counters["table"], _rows_to_markdown(rows), page=page_no,
                                  caption=above.strip().splitlines()[-1] if above.strip() else ""))
            # Code: contiguous lines rendered in a Courier (monospace) font
            mono = [c for c in page.chars if "courier" in c["fontname"].lower()]
            if not mono:
                continue
            by_line: dict[float, list] = {}
            for ch in mono:
                by_line.setdefault(round(ch["top"], 1), []).append(ch)
            blocks, current, last_top = [], [], None
            for top in sorted(by_line):
                text = "".join(c["text"] for c in sorted(by_line[top], key=lambda c: c["x0"]))
                if last_top is not None and top - last_top > 20:  # gap => new code block
                    blocks.append(current)
                    current = []
                current.append(text)
                last_top = top
            blocks.append(current)
            for block in blocks:
                counters["code"] += 1
                items.append(Item("code", counters["code"], "\n".join(block), page=page_no))
    return items


def extract_tables_and_code(path: Path) -> list[Item]:
    return {".md": extract_md, ".html": extract_html, ".pdf": extract_pdf}[path.suffix.lower()](path)


# =============================================================================
# 5. LLM descriptions for tables / code
# =============================================================================

DESCRIBE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You describe tables and code blocks from enterprise knowledge-base articles so they can be "
               "found by semantic search. Write 2-4 plain sentences: what the {kind} shows, what it is used for, "
               "and the key values, codes, thresholds or commands (verbatim). No preamble, no Markdown."),
    ("human", "Article: {kb_id} - {title} ({product} {version}, status: {status})\n"
              "Location: {location}\nCaption: {caption}\n\n{kind} content:\n{content}"),
])


def location_text(item: Item) -> str:
    parts = [f"page {item.page}" if item.page else "", f"section '{item.section}'" if item.section else ""]
    return ", ".join(p for p in parts if p) or "n/a"


def describe_items(pairs: list[tuple[dict, Item]], cfg: Config) -> list[str]:
    chain = DESCRIBE_PROMPT | ChatOpenAI(model=cfg.chat_model, max_retries=3) | StrOutputParser()
    inputs = [{"kind": it.kind, "kb_id": m["kb_id"], "title": m["title"], "product": m.get("product", ""),
               "version": m.get("version", ""), "status": m.get("status", ""), "location": location_text(it),
               "caption": it.caption or "none", "content": it.content[:MAX_ITEM_CHARS]} for m, it in pairs]
    results = chain.batch(inputs, config={"max_concurrency": cfg.describe_concurrency}, return_exceptions=True)
    out = []
    for (meta, item), res in zip(pairs, results):
        if isinstance(res, Exception):
            print(f"  [warn] description failed for {meta['kb_id']} {item.kind} {item.index}: {res}")
            res = f"{item.kind.capitalize()} {item.index} of {meta['kb_id']} ({meta['title']})."
        out.append(res.strip())
    return out


def item_document(meta: dict, item: Item, description: str) -> Document:
    label = f"{'Table' if item.kind == 'table' else 'Code block'} {item.index}"
    ref = f"{label} of {meta['kb_id']} \"{meta['title']}\" ({meta.get('product', '')} {meta.get('version', '')})"
    ref += f" | {location_text(item)}" + (f" | caption: {item.caption}" if item.caption else "")
    body = item.content[:MAX_ITEM_CHARS]
    if item.kind == "code":
        body = f"```{item.language}\n{body}\n```"
    extra = {"content_type": item.kind, "item_index": item.index, "section": item.section, "caption": item.caption}
    if item.page:
        extra["page"] = item.page
    if item.language:
        extra["language"] = item.language
    return Document(page_content=f"{ref}\nDescription: {description}\n\n{body}", metadata={**meta, **extra})


# =============================================================================
# 6. Build all chunks for one domain
# =============================================================================


def build_domain_chunks(domain: str, cfg: Config) -> tuple[list[Document], list[str]]:
    domain_dir = cfg.kb_data_dir / domain
    if not domain_dir.is_dir():
        raise FileNotFoundError(f"KB folder not found: {domain_dir} (check KB_DATA_DIR)")
    manifest = load_manifest(domain_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap,
                                              add_start_index=True)
    docs, ids, pending = [], [], []
    files = sorted(p for p in domain_dir.iterdir() if p.suffix.lower() in (".pdf", ".html", ".md"))

    for path in files:
        pages, file_meta = read_file(path)
        meta = build_metadata(domain, path, file_meta, manifest)
        # Text chunks (tables/code stay inside the text as well)
        for page in pages:
            page.metadata = {**meta, **page.metadata, "content_type": "text"}
        text_chunks = splitter.split_documents(pages)
        for n, chunk in enumerate(text_chunks, start=1):
            chunk.metadata["chunk_index"] = n
            docs.append(chunk)
            ids.append(f"{meta['kb_id']}::text::{n:03d}")
        items = extract_tables_and_code(path)
        pending += [(meta, it) for it in items]
        print(f"  {meta['kb_id']}  {path.suffix[1:]:4}  text_chunks={len(text_chunks):<3} "
              f"tables={sum(i.kind == 'table' for i in items):<2} code={sum(i.kind == 'code' for i in items)}")

    print(f"  Describing {len(pending)} tables/code blocks with '{cfg.chat_model}'...")
    for (meta, item), desc in zip(pending, describe_items(pending, cfg)):
        docs.append(item_document(meta, item, desc))
        ids.append(f"{meta['kb_id']}::{item.kind}::{item.index:02d}")
    return docs, ids


# =============================================================================
# 7. Chroma server - one database per domain
# =============================================================================


def chroma_settings(cfg: Config) -> Settings:
    return Settings(chroma_api_impl="chromadb.api.fastapi.FastAPI", chroma_server_host=cfg.chroma_host,
                    chroma_server_http_port=cfg.chroma_port, anonymized_telemetry=False)


def ensure_database(cfg: Config, database: str) -> None:
    admin = chromadb.AdminClient(chroma_settings(cfg))
    try:
        admin.get_database(database, tenant=cfg.chroma_tenant)
    except Exception:  # noqa: BLE001 - not found
        admin.create_database(database, tenant=cfg.chroma_tenant)
        print(f"  created database '{database}'")


def http_client(cfg: Config, database: str):
    return chromadb.HttpClient(host=cfg.chroma_host, port=cfg.chroma_port, tenant=cfg.chroma_tenant,
                               database=database, settings=Settings(anonymized_telemetry=False))


def populate(domain: str, cfg: Config) -> None:
    database = cfg.databases[domain]
    print(f"\n== {domain} -> database '{database}', collection '{cfg.collection}'")
    ensure_database(cfg, database)
    docs, ids = build_domain_chunks(domain, cfg)

    store = Chroma(client=http_client(cfg, database), collection_name=cfg.collection,
                   embedding_function=OpenAIEmbeddings(model=cfg.embedding_model))
    kb_ids = sorted({d.metadata["kb_id"] for d in docs})
    store.delete(where={"kb_id": {"$in": kb_ids}})  # drop stale chunks of these articles, then upsert
    store.add_documents(docs, ids=ids)
    counts = Counter(d.metadata["content_type"] for d in docs)
    print(f"  stored {len(docs)} chunks ({dict(counts)}) with '{cfg.embedding_model}'")


def stats(domain: str, cfg: Config) -> None:
    database = cfg.databases[domain]
    collection = http_client(cfg, database).get_collection(cfg.collection)
    data = collection.get(include=["metadatas"])
    metas = data["metadatas"]
    print(f"\n== {domain}: database '{database}', collection '{cfg.collection}' -> {collection.count()} chunks")
    print(f"  by content_type: {dict(Counter(m['content_type'] for m in metas))}")
    print(f"  by file_format : {dict(Counter(m['file_format'] for m in metas))}")
    print(f"  by status      : {dict(Counter(m['status'] for m in metas))}")
    print(f"  articles       : {len({m['kb_id'] for m in metas})}")
    sample = next((m for m in metas if m["content_type"] == "table"), metas[0] if metas else {})
    print(f"  sample metadata: {json.dumps(sample, indent=None)[:600]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate the Chroma vector databases from the KB articles.")
    parser.add_argument("--domain", choices=[*DOMAINS, "all"], default="all")
    parser.add_argument("--stats", action="store_true", help="Only print what is stored")
    args = parser.parse_args()

    cfg = load_config()
    domains = list(DOMAINS) if args.domain == "all" else [args.domain]
    try:
        http_client(cfg, "default_database").heartbeat()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Chroma server not reachable at {cfg.chroma_host}:{cfg.chroma_port} "
                         f"(run `make chroma-up`): {exc}") from exc

    for domain in domains:
        stats(domain, cfg) if args.stats else populate(domain, cfg)


if __name__ == "__main__":
    main()
