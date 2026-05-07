# SkillBag Media Governance

SkillBag Media is a companion repository for reusable local media-processing
skills. It is not the normative SkillBag standard.

## Scope

This repository may define reusable workflows for:

- checking local media-processing prerequisites
- transcoding local audio and video
- extracting normalized audio from recordings
- transcribing local audio and video
- creating recording timelines with timestamped transcript and screen text
- summarizing local call transcripts and timelines

It should not encode one organization's meeting taxonomy, project structure,
retention policy, or confidentiality labels.

## Relationship to Other Bags

- `skillbag-utils` provides shared runtime helpers such as
  `skillbag-python-ensure`.
- `skillbag-docs` owns document and image-document processing.
- `skillbag-resources` owns corpus/resource ingestion and indexing.
- `skillbag-media` owns local audio/video mechanics.

## Releases

Release notes should identify new skills, script behavior changes, dependency
changes, and any privacy-relevant behavior.
