"""NetCore Agentic RAG REST API (FastAPI).

The agent itself lives in `scripts/agentic_rag/`; make it importable however the API is started
(uvicorn, pytest, alembic) without relying on PYTHONPATH.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = PROJECT_ROOT / "scripts"
if _SCRIPTS.is_dir() and str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

__version__ = "0.7.0"
