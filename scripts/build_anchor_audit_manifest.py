#!/usr/bin/env python3
"""Build a deterministic frame-review manifest from an AV semantic timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ISSUE_CLASSES = [
    "untargeted-band-mask-or-line",
    "evidence-crop-or-context-loss",
    "missing-or-wrong-callout",
    "annotation-stroke-arrow-or-secondary-line-crosses-content-pixels",
    "icon-text-image-title-or-subtitle-collision",
    "adjacent-state-repeat-double-exposure-or-reset",
    "missing-late-disappearing-or-empty-shell-mg",
    "mobile-evidence-readability",
    "mechanical-pause-repeat-stumble-misread-or-voice-jump",
    "adjacent-window-background-composition-scale-asset-or-motion-not-distinct",
    "source-screenshot-page-number-overlay-crop-dimness-or-shadow-defect",
    "non-evidence-window-missed-context-image-or-visual-metaphor-opportunity",
]


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create per-window and per-anchor frame audit timestamps.")
    parser.add_argument("timeline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reviewers", type=int, default=1, help="Split continuous windows across 1-8 reviewers")
    parser.add_argument("--anchor-pre", type=float, default=0.12)
    parser.add_argument("--anchor-post", type=float, default=0.18)
    args = parser.parse_args()

    data = json.loads(args.timeline.read_text(encoding="utf-8-sig"))
    windows = data.get("semanticWindows") or []
    reviewers = max(1, min(8, args.reviewers))
    if not windows:
        raise SystemExit("semanticWindows is empty")

    result = []
    for index, window in enumerate(windows):
        start, end = float(window["start"]), float(window["end"])
        picks = [
            {"kind": "entry", "time": round(clamp(start + 0.08, start, end), 3)},
        ]
        anchors = window.get("anchors") or []
        for anchor_index, anchor in enumerate(anchors):
            time = float(anchor["time"])
            next_time = float(anchors[anchor_index + 1]["time"]) if anchor_index + 1 < len(anchors) else end
            hold_until = float(anchor.get("holdUntil") or next_time)
            review_end = max(time + 0.05, min(hold_until, next_time, end))
            enter_time = min(time + min(args.anchor_post, 0.12), review_end - 0.02)
            complete_time = min(time + max(args.anchor_post, 0.34), review_end - 0.02)
            hold_time = max(time + 0.05, review_end - 0.08)
            picks.extend([
                {
                    "kind": "anchor-pre",
                    "anchorId": anchor.get("id"),
                    "phrase": anchor.get("phrase"),
                    "target": anchor.get("target"),
                    "time": round(clamp(time - args.anchor_pre, start, end), 3),
                },
                {
                    "kind": "anchor-enter",
                    "anchorId": anchor.get("id"),
                    "phrase": anchor.get("phrase"),
                    "target": anchor.get("target"),
                    "expectedState": anchor.get("resultState"),
                    "holdUntil": anchor.get("holdUntil"),
                    "time": round(clamp(enter_time, start, end), 3),
                },
                {
                    "kind": "anchor-complete",
                    "anchorId": anchor.get("id"),
                    "phrase": anchor.get("phrase"),
                    "target": anchor.get("target"),
                    "expectedState": anchor.get("resultState"),
                    "time": round(clamp(complete_time, start, end), 3),
                },
                {
                    "kind": "anchor-hold",
                    "anchorId": anchor.get("id"),
                    "phrase": anchor.get("phrase"),
                    "target": anchor.get("target"),
                    "expectedState": anchor.get("resultState"),
                    "time": round(clamp(hold_time, start, end), 3),
                },
            ])
        picks.append({"kind": "exit", "time": round(clamp(end - 0.08, start, end), 3)})
        if index < len(windows) - 1:
            boundary = float(windows[index + 1]["start"])
            for offset in (-0.167, -0.100, -0.033, 0.0, 0.033, 0.067, 0.133, 0.200):
                picks.append({"kind": "boundary", "offset": offset, "time": round(clamp(boundary + offset, 0.0, float(data["durationSeconds"])), 3)})
        result.append({
            "windowId": window.get("id"),
            "start": start,
            "end": end,
            "caseNumber": window.get("caseNumber"),
            "spokenClaim": window.get("spokenClaim"),
            "reviewer": index * reviewers // len(windows) + 1,
            "framePicks": picks,
            "requiredChecks": ISSUE_CLASSES,
            "status": "pending",
        })

    output = {
        "schemaVersion": 1,
        "timeline": str(args.timeline.resolve()),
        "durationSeconds": data.get("durationSeconds"),
        "reviewerCount": reviewers,
        "windowCount": len(result),
        "instructions": "Render every listed timestamp at full 1080x1920 and at about 360px mobile width, inspect all twelve classes including annotation/content pixel overlap, adjacent-window differentiation, source screenshot defects, and missed context-image opportunities at enter, complete, and hold states, then replay the same interval at 1x. A repair report is not a pass until the new render is reviewed again.",
        "windows": result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: wrote {len(result)} windows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
