"""SSH into the EC2 instance with the generated key:  uv run --no-sync python iac/ssh.py [command ...]

Without a command it opens an interactive shell (use a real terminal: `make iac-ssh`);
with CMD it runs that and returns, e.g. `make iac-ssh CMD="docker ps"` (also works from the TUI).
On Windows the key's ACL is restricted to the current user first (OpenSSH refuses readable keys).
"""

from __future__ import annotations

import getpass
import os
import shutil
import subprocess
import sys
from pathlib import Path

IAC = Path(__file__).resolve().parent
KEY = IAC / ".keys" / "netcore-rag-ec2.pem"


def public_ip() -> str:
    result = subprocess.run(["terraform", f"-chdir={IAC}", "output", "-raw", "public_ip"],
                            capture_output=True, text=True)
    ip = result.stdout.strip()
    if result.returncode != 0 or not ip or "No outputs" in ip or "Warning" in ip:
        sys.exit("No deployed instance found (make iac-up first)")
    return ip


def protect_key() -> None:
    if not KEY.exists():
        sys.exit(f"Key not found: {KEY} (it is created by make iac-up)")
    if os.name == "nt":
        user = os.environ.get("USERNAME") or getpass.getuser()
        subprocess.run(["icacls", str(KEY), "/inheritance:r", "/grant:r", f"{user}:R"],
                       check=True, capture_output=True)
    else:
        KEY.chmod(0o600)


def main() -> None:
    if not shutil.which("ssh"):
        sys.exit("ssh client not found (Windows: Settings > Optional features > OpenSSH Client)")
    ip = public_ip()
    protect_key()
    # the remote command: arguments, or CMD from the environment (make exports command-line variables)
    command = " ".join(a for a in sys.argv[1:] if a.strip()) or os.environ.get("CMD", "").strip()
    args = ["ssh", "-i", str(KEY), "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15"]
    if command:
        args += ["-o", "BatchMode=yes", f"ubuntu@{ip}", command]
    else:
        args.append(f"ubuntu@{ip}")
    sys.exit(subprocess.call(args))


if __name__ == "__main__":
    main()
