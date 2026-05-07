#!/usr/bin/env python3
"""Create a timestamped transcript and optional screen OCR timeline."""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore[assignment]


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
OCR_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*")
_ASR_PIPE = None


@dataclass
class TranscriptChunk:
    start_s: float
    end_s: float
    text: str


@dataclass
class OcrCheckpoint:
    at_s: float
    text: str
    method: str
    score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a markdown timeline from a local recording.")
    parser.add_argument("--input", required=True, help="Input audio/video recording.")
    parser.add_argument("--output", required=True, help="Output markdown path.")
    parser.add_argument("--title", default="", help="Timeline title.")
    parser.add_argument("--summary", default="", help="Short summary for the metadata block.")
    parser.add_argument("--tags", default="", help="Comma-separated tags.")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    parser.add_argument("--hf-asr-model", default="openai/whisper-large-v3-turbo")
    parser.add_argument("--asr-segment-seconds", type=int, default=60)
    parser.add_argument("--asr-device", choices=("cpu", "mps", "auto"), default="cpu")
    parser.add_argument("--ocr-backend", choices=("auto", "tesseract", "none"), default="auto")
    parser.add_argument("--ocr-interval", type=int, default=20)
    parser.add_argument("--min-ocr-score", type=float, default=80.0)
    parser.add_argument("--ocr-similarity-threshold", type=float, default=0.92)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def seconds_to_hms(value: float) -> str:
    total = max(0, int(round(value)))
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(a=normalize_text(a), b=normalize_text(b)).ratio()


def media_duration_seconds(path: Path, ffmpeg_bin: str) -> float:
    ffprobe_bin = "ffprobe"
    ffmpeg_path = shutil.which(ffmpeg_bin)
    if ffmpeg_path:
        candidate = Path(ffmpeg_path).with_name("ffprobe")
        if candidate.exists():
            ffprobe_bin = str(candidate)
    proc = subprocess.run(
        [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return 0.0
    try:
        return float((proc.stdout or "0").strip())
    except ValueError:
        return 0.0


def convert_video_to_wav(path: Path, ffmpeg_bin: str) -> Tuple[Path, Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="media_timeline_audio_"))
    wav_path = temp_dir / "audio.wav"
    proc = subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(wav_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not wav_path.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError((proc.stderr or "ffmpeg conversion failed").strip())
    return wav_path, temp_dir


def get_asr_pipe(model_id: str, asr_device: str):
    global _ASR_PIPE
    if _ASR_PIPE is not None:
        return _ASR_PIPE

    from transformers import pipeline

    device = "cpu"
    dtype = None
    if asr_device == "mps":
        if torch is None or not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
            raise RuntimeError("MPS requested but not available")
        device = "mps"
        dtype = torch.float16
    elif asr_device == "auto" and torch is not None and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16

    kwargs = {"model": model_id, "device": device}
    if dtype is not None:
        kwargs["dtype"] = dtype
    _ASR_PIPE = pipeline("automatic-speech-recognition", **kwargs)
    return _ASR_PIPE


def transcribe_with_chunks(path: Path, args: argparse.Namespace) -> Tuple[str, List[TranscriptChunk]]:
    if not has_module("transformers"):
        raise RuntimeError("Python module missing: transformers")
    if not has_command(args.ffmpeg_bin):
        raise RuntimeError(f"ffmpeg not available: {args.ffmpeg_bin}")

    asr_input = path
    cleanup_dir: Optional[Path] = None
    try:
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            asr_input, cleanup_dir = convert_video_to_wav(path, args.ffmpeg_bin)

        duration_s = media_duration_seconds(path, args.ffmpeg_bin)
        if duration_s <= 0:
            duration_s = float(max(20, args.asr_segment_seconds))

        pipe = get_asr_pipe(args.hf_asr_model, args.asr_device)
        segment_seconds = max(20, int(args.asr_segment_seconds))
        chunks: List[TranscriptChunk] = []
        full_text: List[str] = []

        with tempfile.TemporaryDirectory(prefix="media_timeline_segments_") as tmp:
            segment_dir = Path(tmp)
            start_s = 0.0
            while start_s < duration_s:
                end_s = min(duration_s, start_s + segment_seconds)
                clip_path = segment_dir / f"segment_{int(start_s):06d}.wav"
                proc = subprocess.run(
                    [
                        args.ffmpeg_bin,
                        "-y",
                        "-ss",
                        str(start_s),
                        "-t",
                        str(max(1.0, end_s - start_s)),
                        "-i",
                        str(asr_input),
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        str(clip_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and clip_path.exists():
                    out = pipe(str(clip_path), chunk_length_s=30)
                    text = str(out.get("text", "") if isinstance(out, dict) else out).strip()
                    if text:
                        chunks.append(TranscriptChunk(start_s=start_s, end_s=end_s, text=text))
                        full_text.append(text)
                start_s = end_s

        return "\n\n".join(full_text).strip(), chunks
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)


def score_ocr_text(text: str) -> float:
    tokens = OCR_TOKEN_RE.findall(text)
    if not tokens:
        return 0.0
    unique_tokens = len({token.lower() for token in tokens})
    return len(tokens) + (0.35 * unique_tokens)


def run_tesseract(path: Path, psm: int) -> Tuple[str, str]:
    proc = subprocess.run(
        ["tesseract", str(path), "stdout", "-l", "eng", "--psm", str(psm)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "", f"tesseract-error:{(proc.stderr or '').strip()}"
    return (proc.stdout or "").strip(), f"tesseract-psm{psm}"


def extract_frame(path: Path, ffmpeg_bin: str, at_s: float, temp_dir: Path) -> Optional[Path]:
    frame_path = temp_dir / f"frame_{int(at_s * 10):06d}.png"
    proc = subprocess.run(
        [ffmpeg_bin, "-y", "-ss", str(at_s), "-i", str(path), "-frames:v", "1", str(frame_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not frame_path.exists():
        return None
    return frame_path


def candidate_ocr_times(chunks: List[TranscriptChunk], duration_s: float, interval: int) -> List[float]:
    screen_words = ("show", "screen", "share", "here", "look", "see", "this", "demo", "settings", "policy")
    times: List[float] = []
    for chunk in chunks:
        text = normalize_text(chunk.text)
        if any(word in text for word in screen_words):
            times.append(chunk.start_s)
            times.append((chunk.start_s + chunk.end_s) / 2.0)

    point = 0.0
    while point <= duration_s:
        if not times or min(abs(point - existing) for existing in times) >= max(8.0, interval / 2):
            times.append(point)
        point += max(5, interval)

    return sorted({round(min(duration_s, max(0.0, item)), 1) for item in times})


def extract_ocr_timeline(path: Path, args: argparse.Namespace, chunks: List[TranscriptChunk]) -> List[OcrCheckpoint]:
    if args.ocr_backend == "none" or path.suffix.lower() not in VIDEO_EXTENSIONS:
        return []
    if not has_command("tesseract"):
        return []

    duration_s = media_duration_seconds(path, args.ffmpeg_bin)
    checkpoints: List[OcrCheckpoint] = []
    last_text = ""
    with tempfile.TemporaryDirectory(prefix="media_timeline_frames_") as tmp:
        temp_dir = Path(tmp)
        for at_s in candidate_ocr_times(chunks, duration_s, args.ocr_interval):
            frame = extract_frame(path, args.ffmpeg_bin, at_s, temp_dir)
            if frame is None:
                continue
            best_text = ""
            best_method = ""
            best_score = 0.0
            for psm in (11, 6):
                text, method = run_tesseract(frame, psm)
                score = score_ocr_text(text)
                if score > best_score:
                    best_text, best_method, best_score = text, method, score
            if best_score < args.min_ocr_score or len(normalize_text(best_text)) < 20:
                continue
            if last_text and similarity(last_text, best_text) >= args.ocr_similarity_threshold:
                continue
            checkpoints.append(OcrCheckpoint(at_s=at_s, text=best_text, method=best_method, score=best_score))
            last_text = best_text
    return checkpoints


def build_markdown(args: argparse.Namespace, input_path: Path, transcript: str, chunks: List[TranscriptChunk], ocr: List[OcrCheckpoint]) -> str:
    title = args.title or input_path.stem.replace("_", " ").replace("-", " ").strip().title()
    generated_at = datetime.now(timezone.utc).isoformat()
    tags = [item.strip() for item in args.tags.split(",") if item.strip()]

    lines: List[str] = [
        "---",
        f"title: {title}",
        f"source_path: {input_path}",
        f"generated_at: {generated_at}",
        f"summary: {args.summary}",
        f"tags: [{', '.join(tags)}]",
        f"asr_method: huggingface-asr:{args.hf_asr_model}",
        f"ocr_method: {args.ocr_backend}",
        "---",
        "",
        "# Timestamped Transcript",
        "",
    ]
    for chunk in chunks:
        lines.append(f"- `[{seconds_to_hms(chunk.start_s)} - {seconds_to_hms(chunk.end_s)}]` {chunk.text}")
    if not chunks:
        lines.append("_No timestamped transcript chunks were generated._")

    lines.extend(["", "# OCR-Derived Screen Notes", ""])
    if ocr:
        lines.append("Temporary frames were extracted for OCR and deleted after processing.")
        lines.append("")
        for point in ocr:
            compact = " ".join(point.text.split())
            lines.append(f"- `[{seconds_to_hms(point.at_s)}]` {compact}")
    else:
        lines.append("_No OCR checkpoints were retained._")

    lines.extend(["", "# Plain Transcript", "", transcript.strip(), ""])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"output exists: {output_path}")
    if not has_command(args.ffmpeg_bin):
        raise RuntimeError(f"ffmpeg not available: {args.ffmpeg_bin}")

    transcript, chunks = transcribe_with_chunks(input_path, args)
    if not transcript.strip():
        raise RuntimeError("no transcript text produced")
    ocr = extract_ocr_timeline(input_path, args, chunks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(args, input_path, transcript, chunks, ocr), encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
