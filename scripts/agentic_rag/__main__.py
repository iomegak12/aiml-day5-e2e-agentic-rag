"""CLI:  make agent-ask Q="..." U=bob     (or: PYTHONPATH=scripts uv run python -m agentic_rag -q "..." -u bob)"""

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ (rag_search, populate_vector_dbs)

from agentic_rag import DEMO_USERS, ask, show_result  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the NetCore Enterprise Agentic RAG agent.")
    parser.add_argument("-q", "--question", required=True)
    parser.add_argument("-u", "--user", default="bob", choices=list(DEMO_USERS),
                        help="alice=guest, bob=employee, carol=admin")
    parser.add_argument("-m", "--mode", default="plan", choices=["plan", "react"],
                        help="plan = Plan-and-Execute (default); react = agent routes with tools")
    parser.add_argument("--quiet", action="store_true", help="No live trace; print the trace table at the end")
    args = parser.parse_args()
    result = ask(args.question, user_id=args.user, verbose=not args.quiet, mode=args.mode)
    show_result(result, show_trace=args.quiet)


if __name__ == "__main__":
    main()
