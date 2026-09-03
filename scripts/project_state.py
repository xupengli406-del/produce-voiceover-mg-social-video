#!/usr/bin/env python3
"""Track single-main-agent production stages and invalidate stale downstream work."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


STATE_FILE = "project-state.json"
STAGES = (
    "brief",
    "evidence",
    "script",
    "audio",
    "timeline",
    "visual",
    "assets",
    "cover",
    "render",
    "audit",
    "delivery",
)
DEPENDENCIES = {
    "brief": (),
    "evidence": ("brief",),
    "script": ("brief", "evidence"),
    "audio": ("script",),
    "timeline": ("audio",),
    "visual": ("timeline",),
    "assets": ("visual",),
    "cover": ("script", "visual"),
    "render": ("timeline", "visual", "assets"),
    "audit": ("render",),
    "delivery": ("cover", "audit"),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stage_record() -> dict:
    return {
        "status": "pending",
        "revision": 0,
        "fingerprint": "",
        "version": "",
        "artifacts": [],
        "approvedAt": "",
        "staleBecause": "",
        "note": "",
    }


def new_state(title: str = "", mode: str = "") -> dict:
    stamp = now()
    return {
        "schemaVersion": 1,
        "architecture": "single-main-agent",
        "project": {"title": title, "mode": mode},
        "createdAt": stamp,
        "updatedAt": stamp,
        "stages": {stage: stage_record() for stage in STAGES},
        "history": [],
    }


def state_path(project_dir: Path) -> Path:
    return project_dir.resolve() / STATE_FILE


def save_state(path: Path, state: dict) -> None:
    state["updatedAt"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state(project_dir: Path) -> tuple[Path, dict]:
    path = state_path(project_dir)
    if not path.is_file():
        raise SystemExit(f"State file is missing: {path}. Run the init command first.")
    state = json.loads(path.read_text(encoding="utf-8-sig"))
    if state.get("schemaVersion") != 1 or state.get("architecture") != "single-main-agent":
        raise SystemExit(f"Unsupported project state: {path}")
    if tuple(state.get("stages", {}).keys()) != STAGES:
        raise SystemExit(f"Project state has an unexpected stage set: {path}")
    return path, state


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_hash(path: Path) -> str:
    if path.is_file():
        return file_hash(path)
    if not path.is_dir():
        raise SystemExit(f"Artifact does not exist: {path}")
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        if child.name == STATE_FILE:
            continue
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash(child).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def display_path(project_dir: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def descendants(stage: str) -> list[str]:
    found: list[str] = []
    frontier = [stage]
    while frontier:
        current = frontier.pop(0)
        for candidate in STAGES:
            if candidate not in found and current in DEPENDENCIES[candidate]:
                found.append(candidate)
                frontier.append(candidate)
    return found


def invalidate_downstream(state: dict, stage: str, reason: str) -> list[str]:
    changed: list[str] = []
    for candidate in descendants(stage):
        record = state["stages"][candidate]
        if record["status"] == "pending" and not record.get("fingerprint"):
            continue
        record["status"] = "stale"
        record["approvedAt"] = ""
        record["staleBecause"] = reason
        changed.append(candidate)
    return changed


def fingerprint(stage: str, version: str, artifacts: Iterable[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    digest.update(stage.encode("utf-8"))
    digest.update(b"\0")
    digest.update(version.encode("utf-8"))
    for path, checksum in artifacts:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(checksum.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def add_history(state: dict, action: str, stage: str, **details: object) -> None:
    entry = {"at": now(), "action": action, "stage": stage}
    entry.update(details)
    state["history"].append(entry)


def cmd_init(args: argparse.Namespace) -> int:
    path = state_path(args.project_dir)
    if path.exists():
        print(f"OK: state already exists at {path}")
        return 0
    state = new_state(args.title, args.mode)
    save_state(path, state)
    print(f"OK: initialized {path}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    path, state = load_state(args.project_dir)
    artifacts: list[dict[str, str]] = []
    pairs: list[tuple[str, str]] = []
    for raw in args.artifacts:
        candidate = raw if raw.is_absolute() else args.project_dir.resolve() / raw
        if not candidate.exists():
            raise SystemExit(f"Artifact does not exist: {candidate}")
        shown = display_path(args.project_dir, candidate)
        checksum = artifact_hash(candidate)
        artifacts.append({"path": shown, "sha256": checksum})
        pairs.append((shown, checksum))
    pairs.sort()
    artifacts.sort(key=lambda item: item["path"])
    new_fingerprint = fingerprint(args.stage, args.version or "", pairs)
    record = state["stages"][args.stage]
    old_fingerprint = record.get("fingerprint", "")
    if old_fingerprint == new_fingerprint and record.get("status") in {"current", "approved"}:
        print(f"OK: {args.stage} is unchanged ({record['status']})")
        return 0
    reason = f"{args.stage} artifact fingerprint changed"
    stale = invalidate_downstream(state, args.stage, reason)
    record.update({
        "status": "current",
        "revision": int(record.get("revision", 0)) + 1,
        "fingerprint": new_fingerprint,
        "version": args.version or "",
        "artifacts": artifacts,
        "approvedAt": "",
        "staleBecause": "",
        "note": args.note or "",
    })
    add_history(state, "record", args.stage, fingerprint=new_fingerprint, invalidated=stale)
    save_state(path, state)
    suffix = f"; invalidated: {', '.join(stale)}" if stale else ""
    print(f"OK: recorded {args.stage} revision {record['revision']}{suffix}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    path, state = load_state(args.project_dir)
    record = state["stages"][args.stage]
    if record.get("status") not in {"current", "approved"} or not record.get("fingerprint"):
        raise SystemExit(f"Stage {args.stage} has no current artifact to approve")
    blocked = [stage for stage in DEPENDENCIES[args.stage] if state["stages"][stage]["status"] != "approved"]
    if blocked:
        raise SystemExit(f"Stage {args.stage} is blocked by: {', '.join(blocked)}")
    record["status"] = "approved"
    record["approvedAt"] = now()
    record["staleBecause"] = ""
    record["note"] = args.note or record.get("note", "")
    add_history(state, "approve", args.stage, note=args.note or "")
    save_state(path, state)
    print(f"OK: approved {args.stage}")
    return 0


def cmd_invalidate(args: argparse.Namespace) -> int:
    path, state = load_state(args.project_dir)
    record = state["stages"][args.stage]
    record["status"] = "stale"
    record["approvedAt"] = ""
    record["staleBecause"] = args.reason
    stale = invalidate_downstream(state, args.stage, args.reason)
    add_history(state, "invalidate", args.stage, reason=args.reason, invalidated=stale)
    save_state(path, state)
    print(f"OK: invalidated {args.stage}" + (f" and {', '.join(stale)}" if stale else ""))
    return 0


def required_through(stage: str) -> set[str]:
    required = {stage}
    frontier = [stage]
    while frontier:
        current = frontier.pop()
        for dependency in DEPENDENCIES[current]:
            if dependency not in required:
                required.add(dependency)
                frontier.append(dependency)
    return required


def cmd_check(args: argparse.Namespace) -> int:
    _, state = load_state(args.project_dir)
    required = required_through(args.through)
    blocked = [stage for stage in STAGES if stage in required and state["stages"][stage]["status"] != "approved"]
    if blocked:
        for stage in blocked:
            record = state["stages"][stage]
            print(f"BLOCKED: {stage}: {record['status']} {record.get('staleBecause', '')}".rstrip())
        return 1
    print(f"OK: all dependencies through {args.through} are approved")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path, state = load_state(args.project_dir)
    print(f"State: {path}")
    for stage in STAGES:
        record = state["stages"][stage]
        detail = f" r{record.get('revision', 0)}"
        if record.get("version"):
            detail += f" {record['version']}"
        if record.get("staleBecause"):
            detail += f" | {record['staleBecause']}"
        print(f"{stage:10} {record['status']:8}{detail}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track one main agent's MG production stages and stale dependencies.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("project_dir", type=Path)
    init.add_argument("--title", default="")
    init.add_argument("--mode", default="")
    init.set_defaults(func=cmd_init)

    record = subparsers.add_parser("record")
    record.add_argument("project_dir", type=Path)
    record.add_argument("stage", choices=STAGES)
    record.add_argument("artifacts", nargs="+", type=Path)
    record.add_argument("--version", default="")
    record.add_argument("--note", default="")
    record.set_defaults(func=cmd_record)

    approve = subparsers.add_parser("approve")
    approve.add_argument("project_dir", type=Path)
    approve.add_argument("stage", choices=STAGES)
    approve.add_argument("--note", default="")
    approve.set_defaults(func=cmd_approve)

    invalidate = subparsers.add_parser("invalidate")
    invalidate.add_argument("project_dir", type=Path)
    invalidate.add_argument("stage", choices=STAGES)
    invalidate.add_argument("--reason", required=True)
    invalidate.set_defaults(func=cmd_invalidate)

    check = subparsers.add_parser("check")
    check.add_argument("project_dir", type=Path)
    check.add_argument("--through", choices=STAGES, required=True)
    check.set_defaults(func=cmd_check)

    status = subparsers.add_parser("status")
    status.add_argument("project_dir", type=Path)
    status.set_defaults(func=cmd_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
