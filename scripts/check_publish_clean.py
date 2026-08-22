#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


BLOCKED = (
    "已配原声",
    "正式版",
    "待原声",
    "视觉预览",
    "字幕草案",
    "测试版",
    "候选版",
    "调试",
)


def iter_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    yield child
        else:
            raise FileNotFoundError(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when audience-facing render sources or subtitles contain internal production labels."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    hits: list[str] = []
    for path in iter_files(args.paths):
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            for label in BLOCKED:
                if label in line:
                    hits.append(f"{path}:{line_number}: {label}")

    if hits:
        print("ERROR: internal production labels found in publish-facing sources:", file=sys.stderr)
        for hit in hits:
            print(f"- {hit}", file=sys.stderr)
        return 1

    print("OK: no blocked internal production labels found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
