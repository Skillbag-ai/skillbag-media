---
name: media-call-summary
description: Summarize local call transcripts, recording timelines, or meeting media notes into reusable markdown summaries, decisions, action items, and follow-ups grounded in transcript evidence. #use/media-transcript #use/media-recording-timeline #use/skillbag-python-ensure
dependencies:
  - name: media-transcript
    required: false
  - name: media-recording-timeline
    required: false
  - name: skillbag-python-ensure
    source: git@github.com:Skillbag-ai/skillbag-utils.git
    version: main
    required: true
allowed-tools: python3 python
metadata:
  author: backupdev
  version: 0.1.0
---

## Parameters

```yaml
required:
  - name: transcript-path
  - name: output-markdown
optional:
  - name: summary-purpose
    default: reusable-call-context
  - name: include-actions
    default: true
  - name: include-decisions
    default: true
  - name: include-open-questions
    default: true
  - name: overwrite
    default: false
  - name: backend
    default: auto
  - name: model-id
    default: t5-small
```

## Instructions

- Use this skill when a local transcript or recording timeline should become a
  concise reusable call summary for later AI work.
- If only a media file is available, use `media-transcript` or
  `media-recording-timeline` first.
- Read the transcript or timeline yourself before finalizing the summary. The
  helper can produce a first-pass draft, but the final output should follow the
  transcript evidence and should not rely blindly on model-ranked or
  heuristic-ranked excerpts.
- Optional helper:
  `python3 .skills/media-call-summary/scripts/media_call_summary.py --transcript-path <transcript-path> --output-markdown <output-markdown>`
- Treat `transcript-path` as source evidence. Do not invent details not
  supported by the transcript.
- `backend=auto` uses Hugging Face when available and falls back to heuristic
  summarization. `backend=hf` requires the Hugging Face backend. These local
  backends are draft aids, not replacements for evidence-grounded agent review.
- Structure the summary for future retrieval:
  - short title
  - source path
  - date when known
  - participants or roles when explicit
  - concise summary
  - key decisions
  - action items
  - open questions
  - notable evidence or timestamps
- Keep summaries generic. Project-specific filing and confidentiality markings
  belong in the consuming workspace.
- Do not overwrite existing summaries unless `overwrite=true`.

## Outputs

- Markdown summary at `output-markdown`.

## File Boundaries

- May read `transcript-path`.
- May create `output-markdown`.
- Must not modify the transcript or original media.
