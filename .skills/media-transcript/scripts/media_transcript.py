#!/usr/bin/env python3
"""Create a markdown transcript from a local audio or video file."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
_HF_ASR_PIPE = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe local audio/video to markdown.")
    parser.add_argument("--input", required=True, help="Input audio/video path.")
    parser.add_argument("--output", required=True, help="Output markdown transcript path.")
    parser.add_argument("--backend", choices=("auto", "whisper-cli", "hf", "huggingface", "none"), default="hf")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--whisper-model", default="base")
    parser.add_argument("--hf-asr-model", default="openai/whisper-base")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    parser.add_argument("--title", default="")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def media_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def transcribe_whisper_cli(path: Path, model: str, language: str) -> Tuple[str, str]:
    if not has_command("whisper"):
        return "", "whisper-cli-unavailable"

    with tempfile.TemporaryDirectory(prefix="media_transcript_whisper_") as tmp:
        tmp_dir = Path(tmp)
        cmd = [
            "whisper",
            str(path),
            "--model",
            model,
            "--output_format",
            "txt",
            "--output_dir",
            str(tmp_dir),
        ]
        if language != "auto":
            cmd.extend(["--language", language])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            return "", f"whisper-cli-error:{stderr or 'non-zero exit'}"
        txt_path = tmp_dir / f"{path.stem}.txt"
        if not txt_path.exists():
            candidates = list(tmp_dir.glob("*.txt"))
            if candidates:
                txt_path = candidates[0]
        if not txt_path.exists():
            return "", "whisper-cli-output-missing"
        return read_text(txt_path).strip(), f"whisper-cli:{model}"


def convert_video_to_wav(path: Path, ffmpeg_bin: str) -> Tuple[Optional[Path], Optional[Path], str]:
    if not has_command(ffmpeg_bin):
        return None, None, "ffmpeg-unavailable"
    temp_dir = Path(tempfile.mkdtemp(prefix="media_transcript_audio_"))
    wav_path = temp_dir / "audio.wav"
    proc = subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(wav_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not wav_path.exists():
        stderr = (proc.stderr or "").strip()
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, None, f"ffmpeg-convert-error:{stderr or 'non-zero exit'}"
    return wav_path, temp_dir, "ok"


def get_hf_asr_pipe(model_id: str):
    global _HF_ASR_PIPE
    if _HF_ASR_PIPE is None:
        from transformers import pipeline

        _HF_ASR_PIPE = pipeline("automatic-speech-recognition", model=model_id)
    return _HF_ASR_PIPE


def transcribe_huggingface(path: Path, model_id: str, language: str, ffmpeg_bin: str) -> Tuple[str, str]:
    if not has_module("transformers"):
        return "", "huggingface-transformers-unavailable"

    asr_input = path
    temp_dir: Optional[Path] = None
    try:
        if media_type(path) == "video":
            wav_path, temp_dir, status = convert_video_to_wav(path, ffmpeg_bin)
            if wav_path is None:
                return "", status
            asr_input = wav_path

        pipe = get_hf_asr_pipe(model_id)
        kwargs = {"chunk_length_s": 30}
        if language != "auto":
            kwargs["generate_kwargs"] = {"language": language, "task": "transcribe"}
        out = pipe(str(asr_input), **kwargs)
        if isinstance(out, dict):
            text = str(out.get("text", "")).strip()
        else:
            text = str(out).strip()
        return text, f"huggingface-asr:{model_id}"
    except Exception as exc:  # pragma: no cover
        return "", f"huggingface-asr-error:{exc}"
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


def transcribe(path: Path, args: argparse.Namespace) -> Tuple[str, str]:
    if args.backend == "none":
        return "", "backend-disabled"
    if args.backend in {"auto", "whisper-cli"}:
        text, method = transcribe_whisper_cli(path, args.whisper_model, args.language)
        if text or args.backend == "whisper-cli":
            return text, method
    if args.backend in {"auto", "hf", "huggingface"}:
        return transcribe_huggingface(path, args.hf_asr_model, args.language, args.ffmpeg_bin)
    return "", "transcription-unavailable"


def build_markdown(path: Path, title: str, text: str, method: str, language: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    display_title = title or path.stem.replace("_", " ").replace("-", " ").strip().title()
    lines = [
        "---",
        f"title: {display_title}",
        f"source_path: {path}",
        f"media_type: {media_type(path)}",
        f"generated_at: {generated_at}",
        f"language: {language}",
        f"extraction_method: {method}",
        "---",
        "",
        "# Transcript",
        "",
        text.strip(),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if media_type(input_path) == "unknown":
        raise ValueError(f"unsupported media extension: {input_path.suffix}")
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"output exists: {output_path}")

    text, method = transcribe(input_path, args)
    if not text.strip():
        raise RuntimeError(f"no transcript text produced ({method})")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(input_path, args.title, text, method, args.language), encoding="utf-8")
    print(f"wrote {output_path} using {method}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
