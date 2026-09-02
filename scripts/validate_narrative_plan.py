#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BRIEF_FIELDS = (
    "核心问题",
    "唯一结论",
    "前 3 秒钩子",
    "开头价值承诺",
    "开头动作钩子（动作 + 观众收益）",
    "情绪起点（观众正在烦什么）",
    "代价放大（继续这样会怎样）",
    "认知翻转",
    "证据缓解",
    "结尾回扣",
    "片尾评论问题（具体、低门槛）",
)


def brief_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"-\s*([^：]+(?:（[^）]+）)?)：\s*(.*)$", line)
        if match:
            values[match.group(1).strip()] = match.group(2).strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the narrative gate before MG rendering.")
    parser.add_argument("brief", type=Path)
    parser.add_argument("timeline", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    values = brief_values(args.brief)
    for field in BRIEF_FIELDS:
        if not values.get(field):
            errors.append(f"brief missing: {field}")

    data = json.loads(args.timeline.read_text(encoding="utf-8-sig"))
    scenes = data.get("scenes") or []
    if not scenes:
        errors.append("timeline has no scenes")
    for scene in scenes:
        label = f"scene {scene.get('id', '?')}"
        for field in ("voiceCueIndexes", "emotionBeat", "spokenQuestion", "spokenClaim", "visualClaim"):
            if not scene.get(field):
                errors.append(f"{label} missing: {field}")
        if scene.get("coverageStatus") != "covered":
            errors.append(f"{label} coverageStatus is not covered")
        for event in scene.get("events") or []:
            for field in ("time", "type", "target"):
                if field not in event or event[field] in ("", None):
                    errors.append(f"{label} event missing: {field}")
            if event.get("type") == "screenshot-proof":
                for field in ("source", "region", "proofClaim"):
                    if not event.get(field):
                        errors.append(f"{label} screenshot-proof missing: {field}")

    for item in errors:
        print("ERROR:", item)
    if errors:
        return 1
    print("OK: narrative plan gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
