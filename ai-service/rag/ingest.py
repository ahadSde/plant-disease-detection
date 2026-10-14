#!/usr/bin/env python3
"""Extract, clean, and section-aware chunk curated agricultural PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pdfplumber


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "agri_docs"
PROCESSING_VERSION = "2.6"

# These headings are kept as boundaries so their content is not mixed with a
# neighbouring topic when chunks are assembled.
SECTION_HEADINGS = {
    "common name", "scientific name", "distribution", "hosts", "symptoms",
    "symptoms and life cycle", "symptoms & life cycle", "impact",
    "detection", "detection and inspection", "detection & inspection",
    "management", "cultural control", "chemical control", "biological control",
    "before planting", "during growth", "after harvest", "resistant varieties",
    "symptom", "cause", "spread", "control", "identification", "description",
    "biology", "scouting", "general management", "precautionary statement",
    "identification of pathogen", "mode of spread and survival",
    "survival and mode of spread", "primary spread", "secondary spread", "vector",
}
SUBSTANTIVE_HEADINGS = {
    "symptom", "symptoms", "symptoms and life cycle", "symptoms & life cycle",
    "impact", "detection", "detection and inspection", "detection & inspection",
    "management", "mode of spread and survival", "biology", "life cycle",
    "field diagnostic symptoms", "integrated disease management", "description",
    "general management", "scouting",
}
METADATA_HEADINGS = {"", "common name", "scientific name", "distribution", "hosts"}

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
TIMESTAMP_RE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+\d{1,2}:\d{2}")
PAGE_MARKER_RE = re.compile(r"^(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?$", re.I)
PHOTO_CAPTION_RE = re.compile(r"\b(?:photo|figure|fig\.?|plate)\s*\d+\s*[.:)]", re.I)
CREDIT_START_RE = re.compile(
    r"^(?:author\b|acknowledg(?:e)?ments?\b|source of (?:images|information)\b|produced with support\b|"
    r"copyright\b|©|all rights reserved\b|this fact sheet is part\b|"
    r"the mobile application is available\b)", re.I
)


def normalize_line(line: str) -> str:
    line = unicodedata.normalize("NFKC", line).replace("\x00", " ").replace("\u00ad", "")
    line = line.replace("\ufb01", "fi").replace("\ufb02", "fl")
    return re.sub(r"\s+", " ", line).strip()


def is_heading(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", line.strip()).rstrip(":").lower()
    if normalized in SECTION_HEADINGS:
        return True
    # Preserve short, explicitly labelled headings found in other extension PDFs.
    return len(line) < 70 and bool(re.fullmatch(r"[A-Z][A-Za-z0-9 /&(),'-]+:", line.strip()))


def strip_inline_boilerplate(text: str) -> str:
    """Remove navigation, captions, credits, timestamps, URLs, and page marks."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(
        r"(?is)\bHome\s*\|\s*About Us\b.*?(?:\bSearch\b|(?=©)|$)", " ", text
    )
    text = re.sub(r"(?i)\bFact sheet\s*[-|:]\s*[^\n]*?(?:\(\d+\))?", " ", text)
    text = re.sub(r"(?i)\bTNAU Agritech Portal\s*::\s*Crop Protection\b", " ", text)
    text = re.sub(r"(?i)/?\s*Plant Health\s*/\s*IPM\s*/\s*Agricultural Pests by Crop\s*/", " ", text)
    text = re.sub(r"(?i)\bMore In-Depth Information\b", " ", text)
    text = re.sub(r"(?is)\bUtah State University sites use cookies\b.*?(?:I agree|$)", " ", text)
    text = URL_RE.sub(" ", text)
    text = re.sub(r"(?i)\b\S+\.html?\b", " ", text)
    text = re.sub(r"(?i)\b\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}\b", " ", text)
    text = re.sub(r"(?i)\bCopyright\s*©?.*?(?:reserved\.?|$)", " ", text)
    text = re.sub(r"(?i)©\s*\d{4}\s*TNAU\b.*?(?:reserved\.?|$)", " ", text)
    text = re.sub(r"(?i)\bAll rights reserved\.?", " ", text)
    text = re.sub(r"(?i)\bAUTHOR\s+[^.\n]+", " ", text)
    text = re.sub(r"(?is)\bProduced with support\b.*$", " ", text)
    text = re.sub(r"(?is)\bThis fact sheet is a part\b.*$", " ", text)
    text = re.sub(r"(?is)\bThe mobile application is available\b.*$", " ", text)
    text = re.sub(r"\b\d+\s*/\s*\d+\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_page_text(text: str) -> str:
    """Clean PDF-extracted lines and discard figure-caption and credit blocks."""
    text = unicodedata.normalize("NFKC", text).replace("\x00", " ").replace("\u00ad", "")
    lines = [normalize_line(line) for line in text.splitlines()]
    output: list[str] = []
    caption_block = False
    credit_block = False
    caption_lines_left = 0
    for line in lines:
        if not line:
            if not caption_block and not credit_block:
                output.append("")
            continue
        if credit_block:
            continue
        if CREDIT_START_RE.match(line):
            credit_block = True
            continue
        if re.match(r"(?i)^Utah State University sites use cookies\b", line):
            continue
        if TIMESTAMP_RE.match(line) or PAGE_MARKER_RE.fullmatch(line):
            continue
        if re.match(r"^(?:Fact sheet\s*[-|:]|Pacific Pests\s*&\s*Pathogens\s*-\s*Full Size Fact Sheets)$", line, re.I):
            continue
        if re.match(r"^(?:https?://|www\.)", line, re.I):
            continue
        if is_heading(line):
            caption_block = False
            caption_lines_left = 0
            output.append(line)
            continue
        if PHOTO_CAPTION_RE.match(line):
            caption_block = True
            caption_lines_left = 24
            continue
        if caption_block:
            caption_lines_left -= 1
            if caption_lines_left <= 0:
                caption_block = False
            continue
        line = strip_inline_boilerplate(line)
        line = re.sub(r"(?i)\bTNAU Agritech Portal\b.*$", " ", line)
        if line:
            output.append(line)
    # Repeated page headers/footers can survive when they vary slightly by page.
    return "\n".join(output)


def extract_pdf_pages(pdf_path: Path) -> list[str]:
    """Use pdfplumber's positional text grouping; it avoids PyPDF2's split words."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = []
        for page in pdf.pages:
            cleaned = clean_page_text(page.extract_text(x_tolerance=3, y_tolerance=3) or "")
            # Browser-saved extension PDFs may include entire image-only pages
            # whose extracted text consists solely of image alt text/captions.
            has_content_heading = any(
                is_heading(line) and line.rstrip(":").lower() in SECTION_HEADINGS
                for line in cleaned.splitlines()
            )
            if len(cleaned.strip()) < 180 and not has_content_heading:
                pages.append("")
            else:
                pages.append(cleaned)
    return remove_repeated_margin_lines(pages)


def remove_repeated_margin_lines(pages: list[str]) -> list[str]:
    """Remove short lines repeated across most pages, conservatively."""
    if len(pages) < 3:
        return pages
    occurrences: dict[str, int] = {}
    for page in pages:
        for line in {line for line in page.splitlines() if line}:
            occurrences[line] = occurrences.get(line, 0) + 1
    threshold = max(3, int(len(pages) * 0.6))
    repeated = {line for line, count in occurrences.items() if count >= threshold and len(line) < 160}
    return ["\n".join(line for line in page.splitlines() if line not in repeated) for page in pages]


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return heading/body pairs, merging wrapped PDF lines into paragraphs."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    parent_heading = ""
    paragraph_lines: list[str] = []
    body_paragraphs: list[str] = []

    def join_wrapped_lines(lines: list[str]) -> str:
        if not lines:
            return ""
        result = lines[0]
        for previous, current in zip(lines, lines[1:]):
            if previous.endswith((".", "!", "?", ":", ";")):
                separator = " "
            elif re.match(r"^(?:Remove|Keep|Do not|Collect|Practise|Plant|Check|Spray|Treatment)\b", current, re.I):
                # Several source PDFs encode successive management actions as
                # separate unpunctuated lines. Restore their sentence boundary.
                separator = ". "
            else:
                separator = " "
            result += separator + current
        return result

    def flush_paragraph() -> None:
        if paragraph_lines:
            body_paragraphs.append(join_wrapped_lines(paragraph_lines).strip())
            paragraph_lines.clear()

    def flush_section() -> None:
        nonlocal heading, parent_heading
        flush_paragraph()
        if heading and not body_paragraphs and heading.lower() in {
            "management", "cultural control", "management - cultural control",
            "identification of pathogen", "survival and mode of spread",
        }:
            parent_heading = heading
            heading = ""
            return
        if heading or body_paragraphs:
            sections.append((heading, body_paragraphs.copy()))
            body_paragraphs.clear()

    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            flush_paragraph()
            continue
        if is_heading(line):
            flush_section()
            heading = line.rstrip(":")
            if parent_heading:
                if heading.lower() in {
                    "before planting", "during growth", "after harvest", "resistant varieties",
                    "chemical control", "cultural control", "mode of spread and survival",
                    "survival and mode of spread", "primary spread", "secondary spread", "vector",
                }:
                    heading = f"{parent_heading} - {heading}"
                    if not parent_heading.lower().startswith("management"):
                        parent_heading = ""
                else:
                    parent_heading = ""
        else:
            paragraph_lines.append(line)
    flush_section()
    if not sections:
        return []
    return [(title, "\n".join(paragraphs)) for title, paragraphs in sections]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    # Do not split on common title abbreviations or decimal points.
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text) if part.strip()]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Pack complete sentences within each section; overlap only at sentence edges."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk-size must be positive and overlap must be between 0 and chunk-size - 1")
    sections = split_sections(text)
    # A few PDFs expose a management subheading plus a one-line introduction
    # as its own section immediately before the actual recommendations. Keep
    # that context with the next management section instead of embedding an
    # otherwise empty heading-only chunk.
    merged_sections: list[tuple[str, str]] = []
    index = 0
    while index < len(sections):
        heading, body = sections[index]
        if (
            heading.strip().lower() in {"management - cultural control", "management - chemical control"}
            and len(body.strip()) < 160
            and index + 1 < len(sections)
            and sections[index + 1][0].strip().lower().startswith("management")
        ):
            next_heading, next_body = sections[index + 1]
            merged_sections.append((next_heading, f"{body.strip()} {next_body}".strip()))
            index += 2
            continue
        merged_sections.append((heading, body))
        index += 1
    sections = merged_sections
    # A PDF title and its short metadata fields are useful context but poor
    # standalone retrieval vectors. Attach that preamble to the first disease
    # content section so top-k slots contain substantive passages.
    substantive_index = next(
        (i for i, (heading, _) in enumerate(sections) if heading.strip().lower() in SUBSTANTIVE_HEADINGS),
        None,
    )
    if substantive_index is not None and substantive_index > 0:
        preamble = sections[:substantive_index]
        if all(heading.strip().lower() in METADATA_HEADINGS for heading, _ in preamble):
            prefix_parts = [body for _, body in preamble if body.strip()]
            heading, body = sections[substantive_index]
            sections = sections[substantive_index:]
            sections[0] = (heading, " ".join(prefix_parts + ([body] if body.strip() else [])))

    chunks: list[str] = []
    for heading, body in sections:
        sentences = split_sentences(body)
        if not sentences and heading:
            sentences = [heading]
            heading = ""
        prefix = f"{heading}: " if heading else ""
        current: list[str] = []
        for sentence in sentences:
            candidate = " ".join(current + [sentence])
            if prefix + candidate and len(prefix + candidate) <= chunk_size:
                current.append(sentence)
                continue
            if current:
                chunks.append((prefix + " ".join(current)).strip())
                carry: list[str] = []
                carry_len = 0
                for prior in reversed(current):
                    if carry and carry_len + len(prior) + 1 > overlap:
                        break
                    carry.insert(0, prior)
                    carry_len += len(prior) + 1
                current = carry
            current.append(sentence)
        if current:
            chunks.append((prefix + " ".join(current)).strip())
    return [chunk for chunk in chunks if chunk]


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def process_pdf(pdf_path: Path, chunk_size: int, overlap: int) -> list[dict[str, object]]:
    pages = extract_pdf_pages(pdf_path)
    text = "\n\n".join(page for page in pages if page)
    chunks = chunk_text(text, chunk_size, overlap)
    source_hash = sha256_file(pdf_path)
    return [
        {
            "source_file": pdf_path.name,
            "source_sha256": source_hash,
            "processing_version": PROCESSING_VERSION,
            "chunk_id": f"{pdf_path.stem}-{index:04d}",
            "text": chunk,
        }
        for index, chunk in enumerate(chunks, start=1)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=800, help="Target characters per chunk")
    parser.add_argument("--overlap", type=int, default=120, help="Target overlap in characters")
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir / "processed"
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {input_dir}.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "ingestion_manifest.json"
    existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest = {
        "processing_version": PROCESSING_VERSION,
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "documents": {},
    }
    for pdf_path in pdfs:
        output_path = output_dir / f"{pdf_path.stem}.jsonl"
        source_hash = sha256_file(pdf_path)
        previous = existing_manifest.get("documents", {}).get(pdf_path.name, {})
        can_skip = (
            existing_manifest.get("processing_version") == PROCESSING_VERSION
            and existing_manifest.get("chunk_size") == args.chunk_size
            and existing_manifest.get("overlap") == args.overlap
            and previous.get("source_sha256") == source_hash
            and output_path.exists()
        )
        if can_skip:
            manifest["documents"][pdf_path.name] = previous
            print(f"{pdf_path.name}: unchanged; retained existing chunks.")
            continue
        records = process_pdf(pdf_path, args.chunk_size, args.overlap)
        with output_path.open("w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
        manifest["documents"][pdf_path.name] = {
            "source_sha256": source_hash,
            "processing_version": PROCESSING_VERSION,
            "chunk_file": output_path.name,
            "chunk_count": len(records),
        }
        print(f"{pdf_path.name}: wrote {len(records)} chunks to {output_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
