"""NetCore make-target terminal UI.  Run: uv run tui.py   (implementation: scripts/make_tui/)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from make_tui import main  # noqa: E402

if __name__ == "__main__":
    main()
