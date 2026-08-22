#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BLOCKED_PATTERNS = (
    (re.compile(r"画面.{0,8}(?:示意|示例)"), "不要朗读画面制作说明；改写为事实条件句"),
    (re.compile(r"画面上.{0,10}(?:拆成|显示|出现|看到|看见)"), "直接描述概念或结果，不要朗读画面调度"),
    (re.compile(r"(?:本图|此图|这张图|那张图).{0,8}(?:示意|示例|展示|显示)"), "不要把图示说明写进口播"),
    (re.compile(r"(?:如图所示|见图|看图)"), "口播应直接解释信息，不依赖观众理解制作指令"),
    (re.compile(r"(?:屏幕上|画面中|镜头里).{0,8}(?:可以)?(?:看到|看见|显示)"), "改成直接面向观众的内容表达"),
    (re.compile(r"这里(?:我们)?(?:可以)?(?:看到|看见)"), "删去主持人式制作口头禅，直接说结论"),
    (re.compile(r"(?:这个|这段)(?:动画|动效).{0,8}(?:展示|显示|说明)"), "不要朗读动效说明"),
    (re.compile(r"(?:系列承接说明|锁定说明|合成对应关系|本说明不朗读|以下内容不朗读)"), "制作记录应移入验收文档，不应出现在最终口播稿或字幕"),
)

REVIEW_TERMS = (
    "对象",
    "执行层",
    "返回值",
    "能力域",
    "编排",
    "方法论",
    "底层逻辑",
    "颗粒度",
)


def iter_text_files(paths: list[Path]):
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
        description="Check spoken scripts and final subtitles for production-language leakage and jargon that needs review."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    blocked: list[str] = []
    review: list[str] = []
    for path in iter_text_files(args.paths):
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            for pattern, advice in BLOCKED_PATTERNS:
                match = pattern.search(line)
                if match:
                    blocked.append(f"{path}:{line_number}: {match.group(0)} — {advice}")
            for term in REVIEW_TERMS:
                if term in line:
                    review.append(f"{path}:{line_number}: {term}")

    if review:
        print("REVIEW: explain or rewrite these potentially abstract terms:")
        for hit in review:
            print(f"- {hit}")

    if blocked:
        print("ERROR: production-language found in audience-facing speech:", file=sys.stderr)
        for hit in blocked:
            print(f"- {hit}", file=sys.stderr)
        return 1

    print("OK: no blocked production-language found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
