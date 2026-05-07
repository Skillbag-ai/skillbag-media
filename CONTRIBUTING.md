# Contributing to SkillBag Media

Keep contributions focused on portable local media workflows.

## Good Contributions

- add or improve reusable audio/video processing skills
- keep transcripts and summaries local-first by default
- make external tools and Python dependencies explicit
- preserve `.skills/SKILLS.md` catalog consistency
- document changed behavior in `CHANGELOG.md`

## Avoid

- organization-specific meeting structures or naming rules
- silent network uploads or cloud transcription
- committing real recordings, transcripts, extracted frames, or summaries
- broad orchestration that belongs in a consuming workspace

Run relevant local checks such as `python3 -m py_compile` for changed Python
helpers and `git diff --check` before proposing changes.
