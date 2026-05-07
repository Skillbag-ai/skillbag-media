#!/usr/bin/env python3
"""Check local media-processing tool availability."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from typing import Any, Dict, List


COMMANDS = ("ffmpeg", "ffprobe", "whisper", "tesseract")
MODULES = ("transformers", "torch", "PIL")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local media-processing prerequisites.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report.")
    parser.add_argument("--require-ffmpeg", action="store_true", help="Mark ffmpeg/ffprobe as required.")
    parser.add_argument("--require-asr", action="store_true", help="Mark local ASR support as required.")
    parser.add_argument("--require-ocr", action="store_true", help="Mark OCR support as required.")
    return parser.parse_args()


def command_status(name: str) -> Dict[str, Any]:
    path = shutil.which(name)
    return {"name": name, "available": path is not None, "path": path or ""}


def module_status(name: str) -> Dict[str, Any]:
    spec = importlib.util.find_spec(name)
    return {"name": name, "available": spec is not None}


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    commands = {item["name"]: item for item in (command_status(name) for name in COMMANDS)}
    modules = {item["name"]: item for item in (module_status(name) for name in MODULES)}

    missing: List[str] = []
    if args.require_ffmpeg:
        for name in ("ffmpeg", "ffprobe"):
            if not commands[name]["available"]:
                missing.append(name)

    whisper_cli = commands["whisper"]["available"]
    hf_asr = modules["transformers"]["available"] and modules["torch"]["available"]
    if args.require_asr and not (whisper_cli or hf_asr):
        missing.append("whisper CLI or transformers+torch")

    if args.require_ocr and not commands["tesseract"]["available"]:
        missing.append("tesseract")

    return {
        "commands": commands,
        "python_modules": modules,
        "capabilities": {
            "ffmpeg_media_conversion": commands["ffmpeg"]["available"] and commands["ffprobe"]["available"],
            "whisper_cli_asr": whisper_cli,
            "huggingface_asr": hf_asr,
            "huggingface_summarization": hf_asr,
            "screen_ocr": commands["tesseract"]["available"],
            "image_preprocessing": modules["PIL"]["available"],
        },
        "missing_required": missing,
        "ok": not missing,
    }


def print_text(report: Dict[str, Any]) -> None:
    print("Media tool check")
    print("")
    print("Commands:")
    for item in report["commands"].values():
        status = "ok" if item["available"] else "missing"
        suffix = f" ({item['path']})" if item["path"] else ""
        print(f"- {item['name']}: {status}{suffix}")

    print("")
    print("Python modules:")
    for item in report["python_modules"].values():
        status = "ok" if item["available"] else "missing"
        print(f"- {item['name']}: {status}")

    print("")
    print("Capabilities:")
    for name, available in report["capabilities"].items():
        print(f"- {name}: {'ok' if available else 'missing'}")

    if report["missing_required"]:
        print("")
        print("Missing required:")
        for item in report["missing_required"]:
            print(f"- {item}")


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
