#!/usr/bin/env python3
"""Summarize a local media transcript or recording timeline."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]*")
TIMESTAMP_RE = re.compile(r"`?\[(\d{1,2}:\d{2}(?::\d{2})?(?:\s*-\s*\d{1,2}:\d{2}(?::\d{2})?)?)\]`?")
STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "on",
    "with",
    "as",
    "by",
    "at",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "into",
    "their",
    "they",
    "we",
    "you",
    "our",
    "your",
    "which",
    "also",
    "can",
    "will",
    "has",
    "have",
    "had",
    "not",
    "but",
    "than",
    "such",
    "using",
    "use",
    "used",
    "about",
    "between",
    "each",
    "other",
    "more",
    "most",
    "all",
    "any",
    "may",
    "should",
    "must",
}


@dataclass
class SummaryResult:
    summary: str
    backend: str
    model_id: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a local call transcript or recording timeline.")
    parser.add_argument("--input", "--transcript-path", dest="input", required=True, help="Input transcript or timeline markdown.")
    parser.add_argument("--output", "--output-markdown", dest="output", required=True, help="Output summary markdown.")
    parser.add_argument("--title", default="", help="Summary title.")
    parser.add_argument("--backend", choices=("auto", "hf", "heuristic"), default="auto")
    parser.add_argument("--model-id", default="t5-small", help="Hugging Face summarization model id.")
    parser.add_argument("--min-words", type=int, default=100)
    parser.add_argument("--max-words", type=int, default=190)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^---\n.*?\n---\n", " ", text, flags=re.S)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", normalize_text(text))
    return [part.strip() for part in parts if len(part.strip()) >= 30]


def transcript_body(text: str) -> str:
    return normalize_text(transcript_section(text))


def transcript_section(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    if "# Plain Transcript" in text:
        return text.split("# Plain Transcript", 1)[1].strip()
    if "# Transcript" in text:
        return text.split("# Transcript", 1)[1].strip()
    return text.strip()


def clean_transcript_text(text: str) -> str:
    text = TIMESTAMP_RE.sub(" ", text)
    text = re.sub(r"^\s*[-*]\s*", " ", text, flags=re.M)
    text = re.sub(r"^#+\s+.*$", " ", text, flags=re.M)
    return normalize_text(text)


def keyword_frequencies(text: str) -> dict[str, int]:
    freq: dict[str, int] = {}
    for token in TOKEN_RE.findall(text.lower()):
        if token in STOPWORDS or len(token) < 3:
            continue
        freq[token] = freq.get(token, 0) + 1
    return freq


def extract_keywords(text: str, limit: int = 10) -> List[str]:
    freq = keyword_frequencies(text)
    return [token for token, _count in sorted(freq.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def natural_join(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def trim_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    trimmed = " ".join(words[:max_words]).strip()
    if not trimmed.endswith((".", "!", "?")):
        trimmed += "."
    return trimmed


def enforce_word_range(summary: str, min_words: int, max_words: int, keywords: List[str]) -> str:
    summary = normalize_text(summary)
    while word_count(summary) < min_words:
        themes = natural_join(keywords[:5]) if keywords else "participants, decisions, action items, and open questions"
        summary = normalize_text(
            summary
            + f" Important recurring themes include {themes}, with details preserved in the source transcript for follow-up."
        )
    return trim_to_words(summary, max_words)


def select_context(text: str, max_words: int = 700) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return text
    freq = keyword_frequencies(text)
    scored: List[Tuple[float, int, str]] = []
    for i, sentence in enumerate(sentences):
        tokens = [token.lower() for token in TOKEN_RE.findall(sentence)]
        score = sum(freq.get(token, 0) for token in tokens if token not in STOPWORDS) / max(len(tokens), 1)
        scored.append((score, i, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected_idx = sorted(i for _score, i, _sentence in scored[:35])

    output: List[str] = []
    count = 0
    for i in selected_idx:
        sentence = sentences[i]
        sentence_words = word_count(sentence)
        if count + sentence_words > max_words:
            break
        output.append(sentence)
        count += sentence_words
    return normalize_text(" ".join(output)) if output else text


class HFSummaryBackend:
    def __init__(self, model_id: str):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_id)

    def generate(self, prompt: str, max_new_tokens: int, min_new_tokens: int) -> str:
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            out_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                min_new_tokens=min_new_tokens,
                num_beams=4,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )
        return normalize_text(self.tokenizer.decode(out_ids[0], skip_special_tokens=True))

    def summarize(self, title: str, text: str, keywords: List[str], min_words: int, max_words: int) -> str:
        context = select_context(text, max_words=700)
        prompt = (
            "summarize: Write one human-readable paragraph between 100 and 190 words. "
            "Summarize this meeting or call transcript for later reuse. Include the main topic, "
            "important decisions, action themes, unresolved questions, and why the conversation matters. "
            "Do not invent details. "
            f"Title: {title}. Content: {context}"
        )
        summary = self.generate(prompt, max_new_tokens=220, min_new_tokens=110)
        return enforce_word_range(summary or context, min_words=min_words, max_words=max_words, keywords=keywords)


def heuristic_summary(title: str, text: str, keywords: List[str], min_words: int, max_words: int) -> str:
    context = select_context(text, max_words=500)
    sentences = split_sentences(context)[:5]
    lead = f"{title} captures a local call or recording transcript intended for later AI context."
    themes = f"Recurring themes include {natural_join(keywords[:6])}." if keywords else ""
    body = " ".join(sentences)
    summary = normalize_text(" ".join(part for part in (lead, body, themes) if part))
    return enforce_word_range(summary, min_words=min_words, max_words=max_words, keywords=keywords)


def summarize(title: str, text: str, backend: str, model_id: str, min_words: int, max_words: int) -> SummaryResult:
    keywords = extract_keywords(text)
    if backend in {"auto", "hf"}:
        try:
            hf = HFSummaryBackend(model_id)
            return SummaryResult(
                summary=hf.summarize(title, text, keywords, min_words, max_words),
                backend="hf",
                model_id=model_id,
            )
        except Exception as exc:
            if backend == "hf":
                raise RuntimeError(f"Failed to initialize Hugging Face summarizer: {exc}") from exc
    return SummaryResult(
        summary=heuristic_summary(title, text, keywords, min_words, max_words),
        backend="heuristic",
        model_id="",
    )


def select_lines(text: str, patterns: List[str], limit: int = 8) -> List[str]:
    output: List[str] = []
    for raw in text.splitlines():
        line = raw.strip(" -\t")
        if len(line) < 12:
            continue
        lowered = line.lower()
        if any(pattern in lowered for pattern in patterns):
            output.append(line)
        if len(output) >= limit:
            break
    return output


def timestamp_evidence(text: str, limit: int = 8) -> List[str]:
    output: List[str] = []
    for raw in text.splitlines():
        if TIMESTAMP_RE.search(raw):
            line = raw.strip()
            if len(line) > 240:
                line = line[:237].rstrip() + "..."
            output.append(line)
        if len(output) >= limit:
            break
    return output


def build_output(input_path: Path, title: str, source_text: str, result: SummaryResult) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    raw_body = transcript_section(source_text)
    decisions = select_lines(raw_body, ["decided", "decision", "agreed", "approved", "confirmed"])
    actions = select_lines(raw_body, ["action", "follow up", "follow-up", "todo", "next step", "will send", "will provide"])
    questions = select_lines(raw_body, ["?", "question", "unclear", "open item", "need to confirm", "follow up on"])
    evidence = timestamp_evidence(source_text)

    lines = [
        "---",
        f"title: {title}",
        f"source_path: {input_path}",
        f"generated_at: {generated_at}",
        f"summary_backend: {result.backend}",
        f"summary_model: {result.model_id}",
        "---",
        "",
        "# Summary",
        "",
        result.summary,
        "",
        "# Decisions",
        "",
    ]
    lines.extend(f"- {item}" for item in decisions) if decisions else lines.append("- None identified explicitly.")
    lines.extend(["", "# Action Items", ""])
    lines.extend(f"- {item}" for item in actions) if actions else lines.append("- None identified explicitly.")
    lines.extend(["", "# Open Questions", ""])
    lines.extend(f"- {item}" for item in questions) if questions else lines.append("- None identified explicitly.")
    lines.extend(["", "# Timestamp Evidence", ""])
    lines.extend(evidence) if evidence else lines.append("- No timestamped evidence found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"output exists: {output_path}")

    source_text = input_path.read_text(encoding="utf-8", errors="replace")
    body = clean_transcript_text(transcript_section(source_text))
    title = args.title or input_path.stem.replace("_", " ").replace("-", " ").strip().title()
    result = summarize(
        title=title,
        text=body,
        backend=args.backend,
        model_id=args.model_id,
        min_words=args.min_words,
        max_words=args.max_words,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_output(input_path, title, source_text, result), encoding="utf-8")
    print(f"wrote {output_path} using {result.backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
