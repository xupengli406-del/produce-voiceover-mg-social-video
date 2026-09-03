#!/usr/bin/env python3
"""Behavior regression checks for the single-main-agent architecture."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_STATE = ROOT / "scripts" / "project_state.py"
AUDIT_MANIFEST = ROOT / "scripts" / "build_anchor_audit_manifest.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, encoding="utf-8", capture_output=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_invalidation(root: Path) -> None:
    project = root / "project"
    project.mkdir()
    run(sys.executable, str(PROJECT_STATE), "init", str(project), "--title", "回归测试")
    artifacts: dict[str, Path] = {}
    for stage in ("brief", "evidence", "script", "audio", "timeline", "visual", "assets", "cover", "render", "audit", "delivery"):
        artifact = project / f"{stage}.txt"
        write(artifact, f"{stage} v1\n")
        artifacts[stage] = artifact
        run(sys.executable, str(PROJECT_STATE), "record", str(project), stage, str(artifact), "--version", "v1")
        run(sys.executable, str(PROJECT_STATE), "approve", str(project), stage)

    write(artifacts["script"], "script v2\n")
    run(sys.executable, str(PROJECT_STATE), "record", str(project), "script", str(artifacts["script"]), "--version", "v2")
    state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
    assert state["architecture"] == "single-main-agent"
    assert state["stages"]["brief"]["status"] == "approved"
    assert state["stages"]["evidence"]["status"] == "approved"
    assert state["stages"]["script"]["status"] == "current"
    for stage in ("audio", "timeline", "visual", "assets", "cover", "render", "audit", "delivery"):
        assert state["stages"][stage]["status"] == "stale", stage


def test_sequential_audit_sections(root: Path) -> None:
    timeline = root / "timeline.json"
    output = root / "audit.json"
    windows = []
    for index in range(30):
        start = float(index * 2)
        windows.append({
            "id": f"window-{index + 1:03d}",
            "start": start,
            "end": start + 2.0,
            "spokenClaim": f"claim {index + 1}",
            "anchors": [{
                "id": f"anchor-{index + 1:03d}",
                "time": start + 0.5,
                "phrase": "测试",
                "target": "target",
                "resultState": "visible",
                "holdUntil": start + 1.8,
            }],
        })
    write(timeline, json.dumps({"durationSeconds": 60.0, "semanticWindows": windows}, ensure_ascii=False))
    run(sys.executable, str(AUDIT_MANIFEST), str(timeline), str(output))
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["architecture"] == "single-main-agent"
    assert manifest["reviewSectionCount"] == 3
    assert len(manifest["windows"]) == 30
    assert {item["reviewSection"] for item in manifest["windows"]} == {1, 2, 3}
    assert all("reviewer" not in item for item in manifest["windows"])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mg-skill-architecture-") as raw:
        root = Path(raw)
        test_invalidation(root)
        test_sequential_audit_sections(root)
    print("OK: single-main-agent architecture regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
