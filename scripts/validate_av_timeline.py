#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def range_ok(item: dict, duration: float) -> bool:
    return (
        number(item.get("start"))
        and number(item.get("end"))
        and 0 <= float(item["start"]) < float(item["end"]) <= duration + 0.01
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate semantic windows and AV anchors before rendering.")
    parser.add_argument("timeline", type=Path)
    args = parser.parse_args()

    data = json.loads(args.timeline.read_text(encoding="utf-8-sig"))
    errors: list[str] = []

    if data.get("schemaVersion") != 2:
        errors.append("schemaVersion must be 2")
    duration = data.get("durationSeconds")
    if not number(duration) or float(duration) <= 0:
        errors.append("durationSeconds must be positive")
        duration = 0.0
    duration = float(duration)

    timing = data.get("timingSource") or {}
    for field in ("audio", "audioSha256", "scriptVersion", "method"):
        if not timing.get(field):
            errors.append(f"timingSource missing: {field}")
    if timing.get("method") in {"character-estimate", "sentence-length-estimate", "image-count-estimate"}:
        errors.append("timingSource method cannot be an estimate")
    if not number(timing.get("speedFactor")) or float(timing.get("speedFactor", 0)) <= 0:
        errors.append("timingSource speedFactor must be positive")

    voice_cues = data.get("voiceCues") or []
    voice_by_id: dict[str, dict] = {}
    previous_end = 0.0
    for index, cue in enumerate(voice_cues, 1):
        label = f"voiceCue {index}"
        cue_id = cue.get("id")
        if not cue_id or cue_id in voice_by_id:
            errors.append(f"{label} id missing or duplicated")
        else:
            voice_by_id[cue_id] = cue
        if not range_ok(cue, duration):
            errors.append(f"{label} invalid range")
        elif float(cue["start"]) + 0.01 < previous_end:
            errors.append(f"{label} overlaps previous cue")
        else:
            previous_end = float(cue.get("end", previous_end))
        if not str(cue.get("text", "")).strip():
            errors.append(f"{label} missing text")

    windows = data.get("semanticWindows") or []
    if not windows:
        errors.append("semanticWindows is empty")
    previous_start = -1.0
    previous_end = None
    window_ids: set[str] = set()
    for index, window in enumerate(windows, 1):
        label = f"semanticWindow {index}"
        window_id = window.get("id")
        if not window_id or window_id in window_ids:
            errors.append(f"{label} id missing or duplicated")
        else:
            window_ids.add(window_id)
        if not range_ok(window, duration):
            errors.append(f"{label} invalid range")
            continue
        start = float(window["start"])
        end = float(window["end"])
        if start < previous_start:
            errors.append(f"{label} is not ordered")
        previous_start = start
        if previous_end is not None and start - previous_end > 0.05 and data.get("gapPolicy") not in {
            "hold-previous", "continuous-overlap"
        }:
            errors.append(f"{label} starts after a visible gap but timeline has no safe gapPolicy")
        previous_end = end
        if end - start < 1.35 and window.get("presentationMode") != "overlay-bridge":
            errors.append(f"{label} is shorter than 1.35s and must use overlay-bridge")
        for field in ("viewerNeed", "spokenClaim"):
            if not str(window.get(field, "")).strip():
                errors.append(f"{label} missing: {field}")
        cue_ids = window.get("voiceCueIds") or []
        if not cue_ids:
            errors.append(f"{label} has no voiceCueIds")
        for cue_id in cue_ids:
            if cue_id not in voice_by_id:
                errors.append(f"{label} references unknown voiceCue: {cue_id}")

        contract = window.get("visualContract") or {}
        if not contract.get("objects"):
            errors.append(f"{label} visualContract has no objects")
        for field in ("action", "startState", "endState", "resultEvidence"):
            if not str(contract.get(field, "")).strip():
                errors.append(f"{label} visualContract missing: {field}")
        if window.get("coverageStatus") != "covered":
            errors.append(f"{label} coverageStatus is not covered")
        evidence = contract.get("evidence") or []
        if len(evidence) == 2 and any(item.get("displayMode") != "stacked" for item in evidence):
            errors.append(f"{label} has two evidence images but is not vertically stacked")
        if len(evidence) > 2 and any(item.get("displayMode") != "anchor-sequence" for item in evidence):
            errors.append(f"{label} has multiple evidence images but is not anchor-sequenced")
        for evidence_index, item in enumerate(evidence, 1):
            if not str(item.get("narrationAnchor", "")).strip():
                errors.append(f"{label} evidence {evidence_index} has no narrationAnchor")
            if item.get("sourceScope") == "official-public" and item.get("privacyMask"):
                errors.append(f"{label} evidence {evidence_index} masks a public official screenshot without a private source")
        hold_until = window.get("holdUntil")
        if not number(hold_until) or not start <= float(hold_until) <= end + 0.01:
            errors.append(f"{label} holdUntil must be inside window")

        spoken_text = "".join(str(voice_by_id.get(cue_id, {}).get("text", "")) for cue_id in cue_ids)
        anchors = window.get("anchors") or []
        if not anchors:
            errors.append(f"{label} has no anchors")
        previous_anchor = start
        for anchor_index, anchor in enumerate(anchors, 1):
            anchor_label = f"{label} anchor {anchor_index}"
            for field in ("id", "phrase", "event", "target", "resultState"):
                if not str(anchor.get(field, "")).strip():
                    errors.append(f"{anchor_label} missing: {field}")
            anchor_time = anchor.get("time")
            if not number(anchor_time) or not start <= float(anchor_time) <= end:
                errors.append(f"{anchor_label} time outside window")
                continue
            anchor_time = float(anchor_time)
            if anchor_time < previous_anchor:
                errors.append(f"{anchor_label} is not ordered")
            previous_anchor = anchor_time
            phrase = str(anchor.get("phrase", "")).replace(" ", "")
            if phrase and phrase not in spoken_text.replace(" ", ""):
                errors.append(f"{anchor_label} phrase not found in linked voice cues")
            anchor_hold = anchor.get("holdUntil")
            if not number(anchor_hold) or not anchor_time <= float(anchor_hold) <= end + 0.01:
                errors.append(f"{anchor_label} holdUntil invalid")

    for index, subtitle in enumerate(data.get("subtitleCues") or [], 1):
        label = f"subtitleCue {index}"
        if not range_ok(subtitle, duration):
            errors.append(f"{label} invalid range")
        text = str(subtitle.get("text", "")).strip()
        if not text:
            errors.append(f"{label} missing text")
        if text.count("\n") > 1:
            errors.append(f"{label} exceeds two lines")

    for item in errors:
        print("ERROR:", item)
    if errors:
        return 1
    print("OK: AV semantic timeline gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
