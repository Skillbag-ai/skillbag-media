#!/usr/bin/env python3
"""Transcode local media or extract normalized audio with ffmpeg."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import List


PROFILES = {
    "audio-wav16k": ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le"],
    "audio-mp3": ["-vn", "-c:a", "libmp3lame", "-q:a", "4"],
    "video-mp4-copy": ["-c", "copy"],
    "video-mp4-h264": ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert local audio/video files with ffmpeg.")
    parser.add_argument("--input", required=True, help="Input media path.")
    parser.add_argument("--output", required=True, help="Output media path.")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="audio-wav16k")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def run_ffmpeg(ffmpeg_bin: str, input_path: Path, output_path: Path, profile_args: List[str], overwrite: bool) -> None:
    if shutil.which(ffmpeg_bin) is None:
        raise RuntimeError(f"ffmpeg not available: {ffmpeg_bin}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_bin, "-y" if overwrite else "-n", "-i", str(input_path), *profile_args, str(output_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(stderr or "ffmpeg failed")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"output exists: {output_path}")
    run_ffmpeg(args.ffmpeg_bin, input_path, output_path, PROFILES[args.profile], args.overwrite)
    print(f"wrote {output_path} using profile {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
