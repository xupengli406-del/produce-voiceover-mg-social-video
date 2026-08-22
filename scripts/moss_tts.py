#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "https://api.mosi.cn"


class MossError(RuntimeError):
    pass


def configured_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value or os.name != "nt":
        return value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            stored, _ = winreg.QueryValueEx(key, name)
        return str(stored).strip()
    except (FileNotFoundError, OSError):
        return ""


def required_api_key() -> str:
    value = configured_value("MOSS_API_KEY")
    if not value:
        raise MossError("MOSS_API_KEY is not configured")
    return value


def base_url() -> str:
    return (configured_value("MOSS_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def request(path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[bytes, str]:
    headers = {"Authorization": f"Bearer {required_api_key()}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base_url() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode("utf-8", errors="replace")
        raise MossError(f"MossAPI HTTP {exc.code}: {body}") from None
    except urllib.error.URLError as exc:
        raise MossError(f"MossAPI connection failed: {exc.reason}") from None


def list_voices() -> list[dict]:
    after: str | None = None
    voices: list[dict] = []
    while True:
        params: dict[str, str | int] = {"limit": 150}
        if after:
            params["after"] = after
        query = urllib.parse.urlencode(params)
        raw, content_type = request(f"/v1/audio/voices?{query}")
        if "json" not in content_type.lower():
            raise MossError("voice list did not return JSON")
        result = json.loads(raw.decode("utf-8"))
        page = result.get("data") or []
        voices.extend(page)
        if not result.get("has_more") or not page:
            break
        after = str(result.get("next_cursor") or "").strip()
        if not after:
            raise MossError("voice list indicates more results but has no next_cursor")
    return voices


def resolve_voice_id(explicit_id: str | None, voice_name: str | None) -> str:
    voice_id = (explicit_id or configured_value("MOSS_VOICE_ID")).strip()
    if voice_id:
        return voice_id
    name = (voice_name or configured_value("MOSS_VOICE_NAME")).strip()
    if not name:
        raise MossError("configure MOSS_VOICE_ID or MOSS_VOICE_NAME")
    matches = [v for v in list_voices() if str(v.get("name", "")).casefold() == name.casefold()]
    if len(matches) != 1:
        raise MossError(f"voice name {name!r} matched {len(matches)} ready voices; use an exact voice id")
    voice_id = str(matches[0].get("id", "")).strip()
    if not voice_id:
        raise MossError("matched voice has no id")
    return voice_id


def output_format(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in {"mp3", "wav"}:
        raise MossError("output extension must be .mp3 or .wav, or pass --format")
    return suffix


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=path.suffix, dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def synthesize(args: argparse.Namespace) -> None:
    text = args.input_file.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise MossError("input file is empty")
    voice_id = resolve_voice_id(args.voice_id, args.voice_name)
    fmt = output_format(args.output, args.format)
    payload = {
        "model": "moss-tts",
        "input": text,
        "voice_id": voice_id,
        "response_format": fmt,
        "delivery_method": "audio",
    }
    if args.version:
        payload["version"] = args.version
    raw, content_type = request("/v1/audio/speech", method="POST", payload=payload)
    if not content_type.lower().startswith("audio/"):
        preview = raw[:4096].decode("utf-8", errors="replace")
        raise MossError(f"speech request did not return audio: {preview}")
    if len(raw) < 1024:
        raise MossError("speech response is unexpectedly small")
    write_atomic(args.output, raw)
    print(json.dumps({
        "status": "downloaded",
        "output": str(args.output.resolve()),
        "bytes": len(raw),
        "content_type": content_type,
        "voice_id": voice_id,
        "model": "moss-tts",
        "version": args.version or "server-default",
    }, ensure_ascii=False))


def list_command(args: argparse.Namespace) -> None:
    voices = list_voices()
    if args.match:
        needle = args.match.casefold()
        voices = [v for v in voices if needle in str(v.get("name", "")).casefold()]
    print(json.dumps([
        {"id": v.get("id"), "name": v.get("name"), "created_at": v.get("created_at")}
        for v in voices
    ], ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate authorized voice-over audio with MossAPI.")
    sub = parser.add_subparsers(dest="command", required=True)
    voices = sub.add_parser("list-voices", help="List ready voices available to the current API tenant.")
    voices.add_argument("--match", help="Filter voice names by substring.")
    voices.set_defaults(func=list_command)
    speech = sub.add_parser("synthesize", help="Generate and atomically save one voice-over file.")
    speech.add_argument("--input-file", type=Path, required=True)
    speech.add_argument("--output", type=Path, required=True)
    speech.add_argument("--voice-id")
    speech.add_argument("--voice-name")
    speech.add_argument("--format", choices=("mp3", "wav"))
    speech.add_argument("--version")
    speech.set_defaults(func=synthesize)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except (MossError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
