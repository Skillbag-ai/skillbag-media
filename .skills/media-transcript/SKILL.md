---
name: media-transcript
description: Transcribe local audio or video files into normalized markdown transcripts using Hugging Face ASR models or local whisper CLI. #use/media-tool-check #use/media-transcode #use/skillbag-python-ensure
dependencies:
  - name: media-tool-check
    required: true
  - name: media-transcode
    required: false
  - name: skillbag-python-ensure
    source: git@github.com:Skillbag-ai/skillbag-utils.git
    version: main
    required: true
allowed-tools: python3 python ffmpeg ffprobe whisper
metadata:
  author: backupdev
  version: 0.1.0
---

## Parameters

```yaml
required:
  - name: input-path
  - name: output-markdown
optional:
  - name: backend
    default: hf
  - name: language
    default: auto
  - name: hf-asr-model
    default: openai/whisper-base
  - name: overwrite
    default: false
```

## Instructions

- Use this skill when a local audio or video file should become a reusable
  markdown transcript for later AI work.
- Use `media-tool-check` first when local ASR or `ffmpeg` availability is
  unknown.
- Prefer the bundled helper:
  `python3 .skills/media-transcript/scripts/media_transcript.py --input <input-path> --output <output-markdown>`
- Treat `input-path` as read-only.
- Do not overwrite an existing transcript unless `overwrite=true`.
- `backend=hf` uses the same local Hugging Face ASR path that the migrated
  Halborn media scripts used for recordings.
- `backend=auto` is still available for compatibility and tries local
  `whisper` CLI first, then Hugging Face ASR when Python dependencies are
  available.
- Video files may be converted to temporary 16 kHz mono WAV for ASR. Temporary
  files must be deleted after processing.
- The generated transcript should include source path, media type, extraction
  method, generated timestamp, caveats, and the plain transcript text.
- Do not call the ChatGPT/OpenAI API for transcription. Hugging Face model
  downloads are local model acquisition, not transcript outsourcing.

## Outputs

- Markdown transcript at `output-markdown`.
- Extraction summary with backend and caveats.

## File Boundaries

- May read `input-path`.
- May create `output-markdown`.
- May create temporary conversion files and must remove them.
- Must not modify the original media file.
