"""Prepare the deployment inputs in iac/.build/ (run by `make iac-plan` / `make iac-up`):

- app.env           : the project .env WITHOUT AWS_* and DOCKERHUB_* (they never leave this machine)
- chroma-data.tgz   : snapshot of the local chroma-data volume (created once; --refresh-chroma re-creates it)

    uv run --no-sync python iac/prepare.py [--engine docker] [--refresh-chroma]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

IAC = Path(__file__).resolve().parent
ROOT = IAC.parent
BUILD = IAC / ".build"
EXCLUDED = re.compile(r"^\s*(?:export\s+)?(AWS_|DOCKERHUB_)")
VOLUME = "netcore-rag_chroma-data"


def write_app_env() -> None:
    source = ROOT / ".env"
    if not source.exists():
        sys.exit("No .env at the project root (cp .env.example .env)")
    lines = source.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not EXCLUDED.match(line)]
    (BUILD / "app.env").write_bytes(("\n".join(kept) + "\n").encode("utf-8"))  # LF for the Linux host
    print(f"app.env: {len(kept)} lines ({len(lines) - len(kept)} AWS_/DOCKERHUB_ lines removed)")


def snapshot_chroma(engine: str, refresh: bool) -> None:
    target = BUILD / "chroma-data.tgz"
    if target.exists() and not refresh:
        print(f"chroma-data.tgz: kept ({target.stat().st_size // 1024} KiB; --refresh-chroma to re-create)")
        return
    check = subprocess.run([engine, "volume", "inspect", VOLUME], capture_output=True, text=True)
    if check.returncode != 0:
        sys.exit(f"Volume {VOLUME} not found: populate Chroma locally first (make up-all)")
    subprocess.run([engine, "run", "--rm", "-v", f"{VOLUME}:/data:ro", "-v", f"{BUILD}:/backup",
                    "alpine:3", "tar", "czf", "/backup/chroma-data.tgz", "-C", "/data", "."], check=True)
    print(f"chroma-data.tgz: {target.stat().st_size // 1024} KiB from volume {VOLUME}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", default="docker")
    parser.add_argument("--refresh-chroma", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(exist_ok=True)
    write_app_env()
    snapshot_chroma(args.engine, args.refresh_chroma)


if __name__ == "__main__":
    main()
