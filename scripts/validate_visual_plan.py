#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIRECTOR_FIELDS = ("attentionTarget", "visualBeat", "payoff", "treatment", "treatmentReason")
BRIEF_FIELDS = (
    "前 3 秒视觉钩子（视觉焦点 + 可见变化 + 信息回报）",
    "首次产品视觉识别（产品名 + 发声锚点 + 官方识别素材）",
)
ASSET_KINDS = {
    "official-original", "official-capture", "live-capture",
    "creator-owned", "generated", "licensed-third-party",
}
ASSET_ROLES = {"identity", "evidence", "explanation", "atmosphere"}
SOURCE_SCOPES = {"official-public", "live-product", "creator-owned", "generated", "third-party"}
IDENTITY_KINDS = {"official-original", "official-capture", "live-capture"}
EVIDENCE_KINDS = IDENTITY_KINDS | {"creator-owned"}
INFO_EVENT_TYPES = {
    "product-recognition", "object-enter", "action-start", "state-change",
    "evidence-reveal", "result-reveal", "transform", "comparison-reveal",
}


def brief_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"-\s*([^：]+(?:（[^）]+）)?)：\s*(.*)$", line)
        if match:
            values[match.group(1).strip()] = match.group(2).strip()
    return values


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def resolve_asset_path(timeline_path: Path, raw: str) -> Path | None:
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate
    roots = [timeline_path.parent, *list(timeline_path.parents)[:4], Path.cwd()]
    for root in roots:
        found = (root / candidate).resolve()
        if found.exists():
            return found
    return (timeline_path.parent / candidate).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate visual direction, product recognition and asset provenance.")
    parser.add_argument("brief", type=Path)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--stage", choices=("directing", "assets"), default="directing")
    args = parser.parse_args()

    errors: list[str] = []
    values = brief_values(args.brief)
    for field in BRIEF_FIELDS:
        if not values.get(field):
            errors.append(f"brief missing: {field}")

    data = json.loads(args.timeline.read_text(encoding="utf-8-sig"))
    if data.get("schemaVersion") != 3:
        errors.append("schemaVersion must be 3 for the visual-direction gate")

    windows = data.get("semanticWindows") or []
    if not windows:
        errors.append("semanticWindows is empty")

    anchors: dict[str, tuple[dict, dict]] = {}
    events: dict[str, tuple[dict, dict]] = {}
    first_three_events: list[dict] = []
    for index, window in enumerate(windows, 1):
        label = f"semanticWindow {window.get('id', index)}"
        plan = window.get("directorPlan") or {}
        for field in DIRECTOR_FIELDS:
            if not str(plan.get(field, "")).strip():
                errors.append(f"{label} directorPlan missing: {field}")
        combined = " ".join(str(plan.get(field, "")) for field in DIRECTOR_FIELDS).lower()
        if combined and any(token in combined for token in ("照着口播显示文字", "口播文字卡", "字幕即可", "generic-agent")):
            errors.append(f"{label} directorPlan is text-only or generic")
        for anchor in window.get("anchors") or []:
            anchor_id = str(anchor.get("id", "")).strip()
            if anchor_id:
                anchors[anchor_id] = (window, anchor)
        for event in window.get("visualEvents") or []:
            event_id = str(event.get("id", "")).strip()
            if not event_id:
                errors.append(f"{label} visualEvent missing: id")
            elif event_id in events:
                errors.append(f"duplicated visualEvent id: {event_id}")
            else:
                events[event_id] = (window, event)
            if is_number(event.get("time")) and float(event["time"]) <= 3.0:
                first_three_events.append(event)

    if not any(str(event.get("type")) in INFO_EVENT_TYPES for event in first_three_events):
        errors.append("0-3s has no information-bearing visual event")

    entities = data.get("entities") or []
    if not entities:
        errors.append("entities is empty; register products that need visual recognition")
    for index, entity in enumerate(entities, 1):
        label = f"entity {entity.get('id', index)}"
        for field in ("id", "type", "firstMentionAnchorId", "recognitionEventId", "identityAssetId"):
            if not str(entity.get(field, "")).strip():
                errors.append(f"{label} missing: {field}")
        names = [str(item).strip() for item in entity.get("spokenNames") or [] if str(item).strip()]
        if not names:
            errors.append(f"{label} spokenNames is empty")
        anchor_entry = anchors.get(str(entity.get("firstMentionAnchorId", "")))
        if not anchor_entry:
            errors.append(f"{label} references unknown firstMentionAnchorId")
        elif names and not any(name.lower() in str(anchor_entry[1].get("phrase", "")).lower() for name in names):
            errors.append(f"{label} first mention anchor phrase does not contain a spoken name")
        event_entry = events.get(str(entity.get("recognitionEventId", "")))
        if not event_entry:
            errors.append(f"{label} references unknown recognitionEventId")
        elif anchor_entry:
            event = event_entry[1]
            if event.get("type") != "product-recognition":
                errors.append(f"{label} recognition event must use type product-recognition")
            event_time = event.get("time")
            anchor_time = anchor_entry[1].get("time")
            if not is_number(event_time) or not is_number(anchor_time):
                errors.append(f"{label} recognition event and anchor need numeric time")
            else:
                delta = float(event_time) - float(anchor_time)
                if delta < -0.20 or delta > 0.35:
                    errors.append(f"{label} recognition event timing delta {delta:.3f}s is outside [-0.20, +0.35]")
                hold = event.get("holdUntil")
                if not is_number(hold) or float(hold) - float(event_time) < 0.80:
                    errors.append(f"{label} recognition state must hold for at least 0.80s")

    if args.stage == "assets":
        assets = data.get("assets") or []
        asset_by_id: dict[str, dict] = {}
        for index, asset in enumerate(assets, 1):
            label = f"asset {asset.get('id', index)}"
            asset_id = str(asset.get("id", "")).strip()
            if not asset_id or asset_id in asset_by_id:
                errors.append(f"{label} id missing or duplicated")
            else:
                asset_by_id[asset_id] = asset
            kind, role, scope = asset.get("kind"), asset.get("role"), asset.get("sourceScope")
            if kind not in ASSET_KINDS:
                errors.append(f"{label} invalid kind: {kind}")
            if role not in ASSET_ROLES:
                errors.append(f"{label} invalid role: {role}")
            if scope not in SOURCE_SCOPES:
                errors.append(f"{label} invalid sourceScope: {scope}")
            if role == "identity" and kind not in IDENTITY_KINDS:
                errors.append(f"{label} identity must use an official or live capture")
            if role == "evidence" and kind not in EVIDENCE_KINDS:
                errors.append(f"{label} evidence must be verifiable")
            if kind == "generated" and role in {"identity", "evidence"}:
                errors.append(f"{label} generated material cannot be identity or evidence")
            if kind == "generated" and not str(asset.get("generationRecord", "")).strip():
                errors.append(f"{label} generated material has no generationRecord")
            if kind == "generated" and not str(asset.get("disclosure", "")).strip():
                errors.append(f"{label} generated material has no disclosure policy")
            if role == "evidence" and not (asset.get("claimIds") or []):
                errors.append(f"{label} evidence has no claimIds")
            asset_path = resolve_asset_path(args.timeline, str(asset.get("path", "")))
            if not asset_path or not asset_path.is_file():
                errors.append(f"{label} local file is missing")
            else:
                expected = str(asset.get("sha256", "")).lower().strip()
                if not expected:
                    errors.append(f"{label} sha256 is missing")
                elif sha256(asset_path) != expected:
                    errors.append(f"{label} sha256 mismatch")
            if kind in {"official-original", "official-capture"}:
                for field in ("sourceUri", "capturedAt"):
                    if not str(asset.get(field, "")).strip():
                        errors.append(f"{label} missing: {field}")

        for index, window in enumerate(windows, 1):
            label = f"semanticWindow {window.get('id', index)}"
            for asset_id in window.get("assetRefs") or []:
                if asset_id not in asset_by_id:
                    errors.append(f"{label} references unknown asset: {asset_id}")
            for event in window.get("visualEvents") or []:
                asset_id = event.get("assetId")
                if asset_id and asset_id not in asset_by_id:
                    errors.append(f"{label} visualEvent references unknown asset: {asset_id}")

        for index, entity in enumerate(entities, 1):
            label = f"entity {entity.get('id', index)}"
            asset = asset_by_id.get(str(entity.get("identityAssetId", "")))
            if not asset:
                errors.append(f"{label} references unknown identityAssetId")
            elif asset.get("role") != "identity" or asset.get("kind") not in IDENTITY_KINDS:
                errors.append(f"{label} identity asset is not an allowed official/live identity")

    for item in errors:
        print("ERROR:", item)
    if errors:
        return 1
    print(f"OK: visual plan gate passed ({args.stage})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
