"""
verify_kb.py - Smoke-test the generated KB with LangChain document loaders.

Checks, for every article listed in data/raw/<domain>/manifest.json:
  - the file exists and loads with the matching loader (PDF / HTML / Markdown)
  - the loaded text is non-trivial and contains the article's KB ID
  - no real vendor / product names leaked into the content

Run via:  make verify
(needs langchain-community, pypdf, beautifulsoup4, lxml - supplied on the fly by `uv run --with`)
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

from langchain_community.document_loaders import BSHTMLLoader, PyPDFLoader, TextLoader

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"
FORBIDDEN = re.compile(r"cisco|webex|vmanage|viptela|velocloud|zoom|microsoft teams", re.IGNORECASE)
MIN_CHARS = 1500

LOADERS = {
    "pdf": lambda p: PyPDFLoader(str(p)),
    "html": lambda p: BSHTMLLoader(str(p), open_encoding="utf-8"),
    "md": lambda p: TextLoader(str(p), encoding="utf-8"),
}


def main() -> int:
    manifests = sorted(RAW.glob("*/manifest.json"))
    if not manifests:
        print("No manifests found under data/raw. Run `make generate` first.")
        return 1

    failures = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"\n== {manifest['domain']} ({manifest['article_count']} articles)")
        for art in manifest["articles"]:
            path = manifest_path.parent / art["file"]
            try:
                docs = LOADERS[art["format"]](path).load()
                text = "\n".join(d.page_content for d in docs)
                problems = []
                if len(text) < MIN_CHARS:
                    problems.append(f"only {len(text)} chars")
                if art["kb_id"] not in text:
                    problems.append("KB ID missing from text")
                if leak := FORBIDDEN.search(text):
                    problems.append(f"real vendor name '{leak.group()}'")
            except Exception as exc:  # noqa: BLE001 - report any loader failure
                docs, text, problems = [], "", [f"{type(exc).__name__}: {exc}"]

            status = "FAIL" if problems else "ok"
            failures += bool(problems)
            print(f"  [{status:4}] {art['kb_id']}  {art['format']:4}  docs={len(docs):<2} chars={len(text):<6}"
                  + (f"  -> {'; '.join(problems)}" if problems else ""))

    print(f"\n{'All checks passed.' if not failures else f'{failures} article(s) failed.'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
