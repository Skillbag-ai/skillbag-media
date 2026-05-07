---
name: media-tool-check
description: Check local media-processing prerequisites such as Python, ffmpeg, ffprobe, whisper CLI, tesseract, transformers, torch, and Pillow before running audio/video skills. #use/skillbag-python-ensure
dependencies:
  - name: skillbag-python-ensure
    source: git@github.com:Skillbag-ai/skillbag-utils.git
    version: main
    required: true
allowed-tools: python3 python ffmpeg ffprobe whisper tesseract
metadata:
  author: backupdev
  version: 0.1.0
---

## Parameters

```yaml
optional:
  - name: require-ffmpeg
    default: true
  - name: require-asr
    default: false
  - name: require-ocr
    default: false
  - name: output-format
    default: text
```

## Instructions

- Use this skill before local audio/video transcription, transcoding, or
  recording timeline generation when tool availability is unknown.
- Prefer the bundled helper for deterministic checks:
  `python3 .skills/media-tool-check/scripts/check_media_tools.py`
- Report missing tools clearly and avoid creating placeholder transcripts.
- `ffmpeg` and `ffprobe` are required for video conversion, audio extraction,
  duration checks, and frame extraction.
- ASR can use either local `whisper` CLI or Python `transformers` with a local
  or downloadable Hugging Face ASR model.
- Call summaries use Python `transformers` and `torch` with a local or
  downloadable Hugging Face summarization model by default.
- Screen OCR can use `tesseract`; Pillow improves image preprocessing.
- Do not install packages or system tools automatically unless the consuming
  workspace explicitly allows that behavior.

## Outputs

- Tool availability report.
- Missing prerequisite list grouped by workflow impact.

## File Boundaries

- May read environment/tool state.
- Must not modify project files.
