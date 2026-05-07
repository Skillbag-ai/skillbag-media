---
name: media-recording-timeline
description: Create a timestamped markdown timeline from a local meeting, demo, walkthrough, or screen-share recording, combining speech transcript chunks with optional screen OCR checkpoints. #use/media-tool-check #use/skillbag-python-ensure
dependencies:
  - name: media-tool-check
    required: true
  - name: skillbag-python-ensure
    source: git@github.com:Skillbag-ai/skillbag-utils.git
    version: main
    required: true
allowed-tools: python3 python ffmpeg ffprobe tesseract
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
  - name: title
  - name: summary
  - name: tags
  - name: hf-asr-model
    default: openai/whisper-large-v3-turbo
  - name: ocr-backend
    default: auto
  - name: ocr-interval
    default: 20
```

## Instructions

- Use this skill for higher-value recordings where a plain transcript is not
  enough, such as product walkthroughs, demos, incident reviews, design calls,
  or screen-share meetings.
- Use `media-tool-check` first when local ASR, `ffmpeg`, or OCR availability is
  unknown.
- Prefer the bundled helper:
  `python3 .skills/media-recording-timeline/scripts/media_recording_timeline.py --input <input-path> --output <output-markdown>`
- Treat `input-path` as read-only.
- Create a timestamped transcript from local ASR.
- Extract temporary frames from screen-share video, run OCR on selected frames,
  and delete temporary frames after processing.
- Keep OCR checkpoints only when they add useful on-screen context and are not
  near-duplicates.
- Do not call cloud transcription or OCR APIs unless a consuming workspace adds
  an explicit policy for that.

## Outputs

- Markdown file containing metadata, timestamped transcript chunks, optional
  OCR-derived screen notes, and a plain transcript.

## File Boundaries

- May read `input-path`.
- May create `output-markdown`.
- May create temporary audio/frame files and must remove them.
- Must not modify the original recording.
