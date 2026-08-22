#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as fh:
        header = fh.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def probe_video(path: Path) -> dict | None:
    probe = shutil.which("ffprobe")
    if not probe:
        return None
    proc = subprocess.run(
        [
            probe,
            "-v", "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,pix_fmt,color_range,color_space,color_transfer,color_primaries,sample_rate,channels",
            "-of", "json",
            str(path),
        ],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "media probe failed")
    return json.loads(proc.stdout)


def full_decode(path: Path) -> bool | None:
    decoder = shutil.which("ffmpeg")
    if not decoder:
        return None
    sink = "NUL" if __import__("os").name == "nt" else "/dev/null"
    proc = subprocess.run(
        [decoder, "-v", "error", "-i", str(path), "-f", "null", sink],
        check=False,
        capture_output=True,
    )
    return proc.returncode == 0


def srt_last_end(path: Path) -> float | None:
    text = path.read_text(encoding="utf-8-sig")
    matches = re.findall(r"-->(?:\s*)(\d{2}):(\d{2}):(\d{2}),(\d{3})", text)
    if not matches:
        return None
    h, m, s, ms = map(int, matches[-1])
    return h * 3600 + m * 60 + s + ms / 1000


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a voiceover MG social-video delivery folder.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--require-horizontal-cover", action="store_true")
    parser.add_argument("--full-decode", action="store_true")
    args = parser.parse_args()

    root = args.output_dir.resolve()
    topic = args.topic
    required = [
        topic + "_小红书成片.mp4",
        topic + "_抖音成片.mp4",
        topic + "_竖封面_3比4.png",
        topic + "_抖音封面_9比16.png",
        topic + "_中文口播稿.txt",
        topic + "_中文字幕.srt",
        topic + "_发布包.md",
    ]
    if args.require_horizontal_cover:
        required.append(topic + "_横封面_4比3.png")

    errors: list[str] = []
    warnings: list[str] = []
    for name in required:
        path = root / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append("missing or empty: " + name)

    cover_rules = {
        topic + "_竖封面_3比4.png": {(1242, 1660), (1200, 1600)},
        topic + "_横封面_4比3.png": {(1600, 1200), (1200, 900)},
        topic + "_抖音封面_9比16.png": {(1080, 1920)},
    }
    for name, allowed in cover_rules.items():
        path = root / name
        if not path.exists():
            continue
        size = png_dimensions(path)
        if size not in allowed:
            errors.append(name + " has unexpected PNG dimensions: " + str(size))

    durations: list[float] = []
    for name in (topic + "_小红书成片.mp4", topic + "_抖音成片.mp4"):
        path = root / name
        if not path.exists():
            continue
        try:
            info = probe_video(path)
        except RuntimeError as exc:
            errors.append(name + " cannot be probed: " + str(exc))
            continue
        if info is None:
            warnings.append("ffprobe unavailable; skipped technical video checks")
            break
        duration = float(info.get("format", {}).get("duration", 0))
        durations.append(duration)
        streams = info.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
        if (video.get("width"), video.get("height")) != (1080, 1920):
            errors.append(name + " is not 1080x1920")
        if video.get("r_frame_rate") != "30/1":
            warnings.append(name + " is not reported as 30fps")
        if video.get("pix_fmt") != "yuv420p":
            warnings.append(name + " pixel format is " + str(video.get("pix_fmt")))
        if video.get("color_range") not in ("tv", None):
            warnings.append(name + " is not TV range")
        if audio.get("sample_rate") not in ("48000", 48000):
            warnings.append(name + " audio sample rate is not 48kHz")
        if args.full_decode:
            decoded = full_decode(path)
            if decoded is False:
                errors.append(name + " failed full decode")
            elif decoded is None:
                warnings.append("ffmpeg unavailable; skipped full decode")

    if len(durations) == 2 and abs(durations[0] - durations[1]) > 0.05:
        errors.append("platform videos have different durations")

    srt = root / (topic + "_中文字幕.srt")
    if srt.exists():
        end = srt_last_end(srt)
        if end is None:
            errors.append("subtitle file has no valid cue timing")
        elif durations and end > max(durations) + 0.1:
            errors.append("subtitle ends after video")

    package = root / (topic + "_发布包.md")
    if package.exists():
        text = package.read_text(encoding="utf-8-sig")
        for marker in ("小红书", "抖音", "标题", "正文", "话题", "CTA", "发布", "复盘"):
            if marker not in text:
                warnings.append("release package may be missing field: " + marker)

    for item in warnings:
        print("WARN:", item)
    for item in errors:
        print("ERROR:", item)
    if errors:
        raise SystemExit(1)
    print("OK: delivery structure and available media checks passed")


if __name__ == "__main__":
    main()
