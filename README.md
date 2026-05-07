# SkillBag Media

SkillBag Media is a companion SkillBag repository for local audio and video
processing in AI-assisted work.

Use it when a workspace needs to transcribe recordings, process local call
videos, extract audio, create timestamped walkthrough timelines, or summarize
meeting transcripts for later context.

It is meant for prompts like:

- "transcribe this call recording"
- "extract audio from this video"
- "make a timeline from this screen-share walkthrough"
- "summarize this transcript into decisions and action items"
- "check whether this machine can process local videos"

The skills are local-first. They use tools such as `ffmpeg`, Tesseract, local
Whisper, and Hugging Face models instead of uploading recordings to a cloud
service by default.

This repository is itself a valid SkillBag source:

- repository instructions live in [AGENTS.md](./AGENTS.md)
- installed skills live under [`.skills/`](./.skills/)
- the skill catalog lives at [`.skills/SKILLS.md`](./.skills/SKILLS.md)

The skills here are meant to be installed into other workspaces as
dependencies. They should stay generic and independent of one organization's
meeting structure, project taxonomy, or retention policy.

## Available Skills

### [media-tool-check](./.skills/media-tool-check/SKILL.md)

Checks whether the local machine has the tools needed for audio/video work.

Key checks:

- `ffmpeg` and `ffprobe`
- local `whisper` CLI
- `tesseract`
- Python modules such as `transformers`, `torch`, and Pillow

Use this before transcription, timeline, OCR, summary, or transcoding work
when the environment is unknown.

### [media-transcode](./.skills/media-transcode/SKILL.md)

Converts local audio/video files or extracts normalized audio from recordings.

Key parameters:

- `input-path` and `output-path` are required
- `profile` defaults to `audio-wav16k`
- `overwrite` defaults to `false`

Common profiles:

- `audio-wav16k`: mono 16 kHz WAV for ASR
- `audio-mp3`: compact audio
- `video-mp4-copy`: remux into MP4 without re-encoding
- `video-mp4-h264`: H.264/AAC MP4 for broad compatibility

### [media-transcript](./.skills/media-transcript/SKILL.md)

Creates a normalized markdown transcript from a local audio or video file.

Key parameters:

- `input-path` and `output-markdown` are required
- `backend` defaults to `hf`
- `language` defaults to `auto`
- `hf-asr-model` defaults to `openai/whisper-base`

Behavior:

- uses local Hugging Face ASR by default, matching the migrated recording
  workflow
- can use local Whisper CLI through `backend=auto` or `backend=whisper-cli`
- converts video to temporary normalized audio when needed
- writes markdown with source metadata and transcript text
- deletes temporary conversion files after processing

### [media-recording-timeline](./.skills/media-recording-timeline/SKILL.md)

Creates a timestamped markdown timeline from a local meeting, demo,
walkthrough, or screen-share recording.

Key parameters:

- `input-path` and `output-markdown` are required
- `title`, `summary`, and `tags` are optional
- `hf-asr-model` defaults to `openai/whisper-large-v3-turbo`
- `ocr-backend` defaults to `auto`

Behavior:

- creates timestamped transcript chunks
- extracts temporary video frames for screen OCR when useful
- keeps OCR checkpoints that add screen context
- deletes temporary audio and frame files

### [media-call-summary](./.skills/media-call-summary/SKILL.md)

Summarizes a local transcript or recording timeline into reusable meeting
context using the existing Hugging Face-first summary pattern.

Key parameters:

- `transcript-path` and `output-markdown` are required
- `summary-purpose` defaults to `reusable-call-context`
- decision, action item, and open question sections are enabled by default
- `backend` defaults to `auto`, which uses Hugging Face when available and
  falls back to a heuristic summary
- `model-id` defaults to `t5-small`

Use this after `media-transcript` or `media-recording-timeline` when the
result should become easier to reuse in future AI work or resource indexes.

## How To Use

Typical usage is to add this repository as a SkillBag dependency from another
workspace, usually alongside:

- [`skillbag-utils`](https://github.com/Skillbag-ai/skillbag-utils) for shared
  runtime helpers such as Python checks
- [`skillbag-resources`](https://github.com/Skillbag-ai/skillbag-resources)
  when transcripts, timelines, or summaries should be ingested into a local
  knowledge base
- [`skillbag-docs`](https://github.com/Skillbag-ai/skillbag-docs) when the
  workflow also needs PDF, Word, OCR, table, or diagram processing

Once installed, users can ask in natural language. For example, an agent with
these skills available can understand that "transcribe this recording",
"process this walkthrough video", "extract the audio", and "summarize this
call" all map to this media skill set.

## Design Notes

SkillBag Media is for local media mechanics. It does not decide where a
project stores call notes, how long recordings are retained, or which
confidentiality labels apply. Those decisions belong in the consuming
workspace.

Generated transcripts and summaries can contain sensitive conversation and
screen-share content. Treat them with the same care as the original recording.

## Repository Layout

- [AGENTS.md](./AGENTS.md): repository-level installation metadata
- [README.md](./README.md): project overview
- [CONTRIBUTING.md](./CONTRIBUTING.md): contribution guidance
- [GOVERNANCE.md](./GOVERNANCE.md): media-skill repository governance
- [SUSTAINABILITY.md](./SUSTAINABILITY.md): funding and maintenance model
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md): collaboration standards
- [SECURITY.md](./SECURITY.md): security reporting guidance
- [CHANGELOG.md](./CHANGELOG.md): notable repository changes
- [LICENSE.md](./LICENSE.md): MIT license
- [`.skills/SKILLS.md`](./.skills/SKILLS.md): low-cost skill discovery catalog

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Security

See [SECURITY.md](./SECURITY.md).

## License

Released under the MIT license. See [LICENSE.md](./LICENSE.md).
