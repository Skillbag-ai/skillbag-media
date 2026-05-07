---
name: media-transcode
description: Convert local audio/video files or extract normalized audio from recordings using ffmpeg for later transcription, indexing, or sharing. #use/media-tool-check #use/skillbag-python-ensure
dependencies:
  - name: media-tool-check
    required: true
  - name: skillbag-python-ensure
    source: git@github.com:Skillbag-ai/skillbag-utils.git
    version: main
    required: true
allowed-tools: python3 python ffmpeg ffprobe
metadata:
  author: backupdev
  version: 0.1.0
---

## Parameters

```yaml
required:
  - name: input-path
  - name: output-path
optional:
  - name: profile
    default: audio-wav16k
  - name: overwrite
    default: false
  - name: ffmpeg-bin
    default: ffmpeg
```

## Instructions

- Use this skill when a local recording needs audio extraction, audio
  normalization, or basic video conversion before transcription or sharing.
- Use `media-tool-check` first when `ffmpeg` availability is unknown.
- Prefer the bundled helper:
  `python3 .skills/media-transcode/scripts/media_transcode.py --input <input-path> --output <output-path> --profile <profile>`
- Treat the input media file as read-only.
- Do not overwrite existing outputs unless `overwrite=true`.
- Common profiles:
  - `audio-wav16k`: mono 16 kHz WAV for ASR
  - `audio-mp3`: compact MP3 audio
  - `video-mp4-copy`: MP4 container remux without re-encoding
  - `video-mp4-h264`: H.264/AAC MP4 for broad compatibility

## Outputs

- Converted or extracted media at `output-path`.
- Short conversion summary including selected profile.

## File Boundaries

- May read `input-path`.
- May create `output-path`.
- Must not overwrite existing outputs unless requested.
