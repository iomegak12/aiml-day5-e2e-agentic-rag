"""
assign_access_levels.py - Patch the RBAC `access_level` metadata into existing Chroma chunks (no re-embedding).

Rule (by article_type, see ACCESS_LEVEL_BY_TYPE in populate_vector_dbs.py):
  faq, help                    -> public
  config, runbook, reference   -> internal
  policy                       -> restricted

Usage:  make assign-access-levels      (or: uv run scripts/assign_access_levels.py)
"""

from __future__ import annotations

from collections import Counter

from populate_vector_dbs import ACCESS_LEVEL_BY_TYPE, DOMAINS, http_client, load_config


def main() -> None:
    cfg = load_config()
    for domain in DOMAINS:
        collection = http_client(cfg, cfg.databases[domain]).get_collection(cfg.collection)
        data = collection.get(include=["metadatas"])
        metadatas = [{**m, "access_level": ACCESS_LEVEL_BY_TYPE.get(m.get("article_type", ""), "restricted")}
                     for m in data["metadatas"]]
        collection.update(ids=data["ids"], metadatas=metadatas)  # metadata only - embeddings untouched

        stored = collection.get(include=["metadatas"])["metadatas"]
        by_level = Counter(m["access_level"] for m in stored)
        articles = {lvl: sorted({m["kb_id"] for m in stored if m["access_level"] == lvl}) for lvl in by_level}
        print(f"\n== {domain} ({cfg.databases[domain]}): {len(stored)} chunks updated")
        for level in ("public", "internal", "restricted"):
            print(f"  {level:10} chunks={by_level.get(level, 0):<3} articles={', '.join(articles.get(level, []))}")


if __name__ == "__main__":
    main()
