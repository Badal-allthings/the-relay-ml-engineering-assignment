
import json
import re
from pathlib import Path

import pymupdf


PAPERS_DIR = Path("data/papers")
OUTPUT_FILE = Path("data/passages.json")

PAPER_TITLES = {
    "attention_is_all_you_need_v7.pdf": "Attention Is All You Need",
    "moshi_v1.pdf": "Moshi: a speech-text foundation model for real-time dialogue",
    "dynamic_chunking_v2.pdf": (
        "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling"
    ),
}

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving readable text."""
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_into_chunks(text: str) -> list[str]:
    """Split text into overlapping character-based chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def extract_passages() -> list[dict]:
    passages = []

    for pdf_path in sorted(PAPERS_DIR.glob("*.pdf")):
        paper_title = PAPER_TITLES.get(pdf_path.name)

        if not paper_title:
            print(f"Skipping unknown PDF: {pdf_path.name}")
            continue

        print(f"Processing: {paper_title}")

        document = pymupdf.open(pdf_path)

        for page_index, page in enumerate(document):
            page_text = clean_text(page.get_text())

            if not page_text:
                continue

            chunks = split_into_chunks(page_text)

            for chunk_index, chunk in enumerate(chunks):
                passages.append({
                    "passage_id": (
                        f"{pdf_path.stem}_p{page_index + 1}_c{chunk_index + 1}"
                    ),
                    "paper_title": paper_title,
                    "source_file": pdf_path.name,
                    "page_number": page_index + 1,
                    "chunk_index": chunk_index + 1,
                    "text": chunk,
                })

        document.close()

    return passages


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    passages = extract_passages()

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(passages, file, ensure_ascii=False, indent=2)

    print("\nExtraction complete.")
    print(f"Total passages: {len(passages)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
