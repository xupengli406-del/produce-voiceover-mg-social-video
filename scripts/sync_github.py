#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, capture: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, commit, push, and verify this Skill repository.")
    parser.add_argument("--message", help="Commit message. A timestamped maintenance message is used when omitted.")
    args = parser.parse_args()

    subprocess.run([sys.executable, str(ROOT / "scripts" / "repo_check.py")], cwd=ROOT, check=True)
    run("git", "rev-parse", "--is-inside-work-tree")
    remote = run("git", "remote", "get-url", "origin")
    if not remote:
        raise SystemExit("origin remote is not configured")

    run("git", "diff", "--check")
    run("git", "add", "-A")
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode == 0:
        print("OK: no changes to sync")
        return 0
    if staged.returncode != 1:
        raise SystemExit("unable to inspect staged changes")
    run("git", "diff", "--cached", "--check")

    message = args.message or "chore: sync skill update " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run("git", "commit", "-m", message, capture=False)
    branch = run("git", "branch", "--show-current") or "main"
    run("git", "push", "-u", "origin", branch, capture=False)

    local_sha = run("git", "rev-parse", "HEAD")
    remote_line = run("git", "ls-remote", "origin", f"refs/heads/{branch}")
    remote_sha = remote_line.split()[0] if remote_line else ""
    if local_sha != remote_sha:
        raise SystemExit(f"remote verification failed: local={local_sha} remote={remote_sha or 'missing'}")
    print(f"OK: synced {branch} at {local_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
