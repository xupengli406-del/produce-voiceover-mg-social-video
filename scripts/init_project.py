#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from project_state import new_state, save_state


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
TEMPLATES = ASSETS / "templates"
MG_TEMPLATE = ASSETS / "mg-template"


def safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]+', "-", value).strip(" .")
    return value or "未命名主题"


def render_template(source: Path, destination: Path, replacements: dict[str, str]) -> None:
    text = source.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    destination.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a portable original-voice MG social video project.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--mode", choices=("information", "concept", "demo"), default="information")
    parser.add_argument("--platforms", default="小红书,抖音")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--renderer", choices=("remotion", "canvas-legacy"), default="remotion")
    args = parser.parse_args()

    root = args.project_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit("Project directory already exists and is not empty: " + str(root))

    title = safe_name(args.title)
    for relative in ("input", "work/audio", "work/visual", "work/qa", "outputs", "evidence"):
        (root / relative).mkdir(parents=True, exist_ok=True)

    replacements = {
        "TITLE": title,
        "MODE": args.mode,
        "PLATFORMS": args.platforms,
        "DURATION": str(round(args.duration, 3)),
    }
    render_template(TEMPLATES / "brief.md", root / "brief.md", replacements)
    render_template(TEMPLATES / "timeline.json", root / "work" / "timeline.json", replacements)
    render_template(TEMPLATES / "publish-package.md", root / "outputs" / (title + "_发布包.md"), replacements)
    source = ASSETS / "remotion-template" if args.renderer == "remotion" else MG_TEMPLATE
    folder = "remotion" if args.renderer == "remotion" else "mg-template"
    shutil.copytree(source, root / "work" / "visual" / folder,
                    ignore=shutil.ignore_patterns("node_modules", ".cache", "__pycache__"))

    manifest = {
        "title": title,
        "mode": args.mode,
        "platforms": [item.strip() for item in args.platforms.split(",") if item.strip()],
        "targetDurationSeconds": args.duration,
        "inputs": {
            "voice": "",
            "script": "",
            "visualReferences": [],
            "sourceEvidence": [],
        },
        "status": "initialized",
        "renderer": args.renderer,
    }
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save_state(root / "project-state.json", new_state(title=title, mode=args.mode))
    print(str(root))


if __name__ == "__main__":
    main()
