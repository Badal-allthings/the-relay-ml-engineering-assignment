
import pytest

from src import ingest


def test_clean_text_normalizes_whitespace():
    text = "trans-\nformer   uses\n multiple spaces."

    result = ingest.clean_text(text)

    assert result == "transformer uses multiple spaces."


def test_split_into_chunks_preserves_overlap():
    text = "A" * 2500

    chunks = ingest.split_into_chunks(text)

    assert len(chunks) == 3
    assert len(chunks[0]) == 1200
    assert len(chunks[1]) == 1200
    assert len(chunks[2]) == 400
    assert chunks[0][-150:] == chunks[1][:150]


def test_split_into_chunks_handles_short_text():
    text = "A short research passage."

    chunks = ingest.split_into_chunks(text)

    assert chunks == [text]


def test_split_into_chunks_handles_empty_text():
    assert ingest.split_into_chunks("") == []


def test_extract_passages_preserves_metadata(tmp_path, monkeypatch):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()

    pdf_path = papers_dir / "attention_is_all_you_need_v7.pdf"
    pdf_path.touch()

    class FakePage:
        def __init__(self, text):
            self.text = text

        def get_text(self):
            return self.text

    class FakeDocument:
        def __init__(self):
            self.pages = [
                FakePage("Scaled dot product attention uses queries and keys."),
                FakePage(""),
            ]
            self.closed = False

        def __iter__(self):
            return iter(self.pages)

        def close(self):
            self.closed = True

    fake_document = FakeDocument()

    monkeypatch.setattr(ingest, "PAPERS_DIR", papers_dir)
    monkeypatch.setattr(
        ingest.pymupdf,
        "open",
        lambda path: fake_document,
    )

    passages = ingest.extract_passages()

    assert len(passages) == 1

    passage = passages[0]

    assert passage["paper_title"] == "Attention Is All You Need"
    assert passage["source_file"] == "attention_is_all_you_need_v7.pdf"
    assert passage["page_number"] == 1
    assert passage["chunk_index"] == 1
    assert passage["passage_id"] == "attention_is_all_you_need_v7_p1_c1"
    assert "queries and keys" in passage["text"]
    assert fake_document.closed is True


def test_extract_passages_skips_unknown_papers(tmp_path, monkeypatch):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()

    unknown_pdf = papers_dir / "unknown_paper.pdf"
    unknown_pdf.touch()

    monkeypatch.setattr(ingest, "PAPERS_DIR", papers_dir)

    passages = ingest.extract_passages()

    assert passages == []
