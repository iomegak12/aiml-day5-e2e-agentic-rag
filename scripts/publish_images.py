"""Publish the project images to Docker Hub: api, mcp and web as <user>/netcore-rag-<name>:<version> and :latest.

    uv run --env-file .env scripts/publish_images.py --version 0.10.0 [--user iomega] [--engine docker] [--dry-run]

Login uses DOCKERHUB_USERNAME + DOCKERHUB_TOKEN (an access token from hub.docker.com > Account settings >
Personal access tokens) via --password-stdin; the token is never printed or put on a command line.
The images must exist locally (make publish builds them first).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

IMAGES = ("api", "mcp", "web")


def run(cmd: list[str], dry_run: bool, stdin: str | None = None) -> str:
    print("$", " ".join(cmd), flush=True)
    if dry_run:
        return ""
    result = subprocess.run(cmd, input=stdin, text=True, capture_output=stdin is not None)
    if result.returncode != 0:
        sys.exit(f"failed ({result.returncode}): {' '.join(cmd)}\n{(result.stderr or '').strip()}")
    return result.stdout or ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True)
    parser.add_argument("--user", default=os.environ.get("DOCKERHUB_USERNAME", "iomega").strip() or "iomega")
    parser.add_argument("--engine", default="docker")
    parser.add_argument("--dry-run", action="store_true", help="print the commands only")
    args = parser.parse_args()

    token = os.environ.get("DOCKERHUB_TOKEN", "").strip()
    if not token and not args.dry_run:
        sys.exit("DOCKERHUB_TOKEN is not set in .env (create an access token on hub.docker.com)")
    run([args.engine, "login", "docker.io", "-u", args.user, "--password-stdin"], args.dry_run, stdin=token)

    pushed = []
    for name in IMAGES:
        local = f"localhost/netcore-rag-{name}:{args.version}"
        for tag in (args.version, "latest"):
            remote = f"docker.io/{args.user}/netcore-rag-{name}:{tag}"
            run([args.engine, "tag", local, remote], args.dry_run)
            run([args.engine, "push", remote], args.dry_run)
            pushed.append(remote)

    print("\nPublished:" if not args.dry_run else "\nWould publish:")
    for remote in pushed:
        print("  ", remote)
    if not args.dry_run:
        print(f"\nhttps://hub.docker.com/u/{args.user}")


if __name__ == "__main__":
    main()
