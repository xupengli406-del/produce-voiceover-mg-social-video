#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".js", ".html", ".json", ".yaml", ".yml", ".txt", ".toml", ".css"}
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/story-and-motion.md",
    "references/audio-and-timing.md",
    "references/delivery-and-qa.md",
    "references/orchestration-and-state.md",
    "scripts/init_project.py",
    "scripts/project_state.py",
    "scripts/test_single_agent_architecture.py",
    "scripts/validate_delivery.py",
)
SECRET_PATTERNS = (
    re.compile(r"gh[opusr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"(?i)\b[A-Z]:\\(?:Users|Documents|Desktop|Downloads)\\"),
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
)


def iter_files() -> list[Path]:
    return [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty: {relative}")

    skill = ROOT / "SKILL.md"
    if skill.exists():
        body = skill.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", body, re.DOTALL)
        if not match:
            errors.append("SKILL.md has no valid YAML frontmatter block")
        else:
            frontmatter = match.group(1)
            name = re.search(r"(?m)^name:\s*(.+?)\s*$", frontmatter)
            description = re.search(r"(?m)^description:\s*(.+?)\s*$", frontmatter)
            if not name or name.group(1).strip() != ROOT.name:
                errors.append("SKILL.md name does not match repository folder")
            if not description or len(description.group(1).strip()) < 20:
                errors.append("SKILL.md description is missing or too short")

    for path in iter_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"file exceeds 10 MiB repository limit: {relative}")
        if path.name.startswith(".env") and path.name != ".env.example":
            errors.append(f"environment file must not be committed: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"text file is not UTF-8: {relative}")
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {relative}: {pattern.pattern}")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                errors.append(f"machine-local absolute path in {relative}")
        if path.suffix.lower() == ".py":
            try:
                ast.parse(text, filename=relative)
            except SyntaxError as exc:
                errors.append(f"Python syntax error in {relative}: {exc}")
        if path.suffix.lower() == ".json" and "{{" not in text:
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"JSON syntax error in {relative}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    regression = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "test_single_agent_architecture.py")],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if regression.returncode != 0:
        print(regression.stdout.rstrip())
        print("ERROR: single-main-agent architecture regression checks failed")
        return 1
    print(regression.stdout.rstrip())
    print("OK: repository checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
