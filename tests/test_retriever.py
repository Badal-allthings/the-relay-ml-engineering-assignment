
import pytest

from src.retriever import PaperRetriever, tokenize


@pytest.fixture
def sample_passages():
    return [
        {
            "paper_title": "Attention Is All You Need",
            "source_file": "attention.pdf",
            "page_number": 4,
            "chunk_index": 1,
            "passage_id": "attention_p4_c1",
            "text": (
                "Scaled dot product attention uses queries, keys and values. "
                "The query and key dot products are scaled by the square root "
                "of the key dimension before applying softmax."
            ),
        },
        {
            "paper_title": "Moshi",
            "source_file": "moshi.pdf",
            "page_number": 10,
            "chunk_index": 1,
            "passage_id": "moshi_p10_c1",
            "text": (
                "Moshi uses audio tokens and a neural audio codec "
                "for real-time speech generation."
            ),
        },
        {
            "paper_title": "Dynamic Chunking",
            "source_file": "dynamic_chunking.pdf",
            "page_number": 3,
            "chunk_index": 1,
            "passage_id": "dynamic_p3_c1",
            "text": (
                "Dynamic chunking learns boundaries for hierarchical "
                "sequence processing and byte-level modeling."
            ),
        },
    ]


def test_tokenize_removes_common_words_and_artifacts():
    tokens = tokenize("The Transformer uses attention EOS PAD")

    assert "transformer" in tokens
    assert "attention" in tokens
    assert "the" not in tokens
    assert "eos" not in tokens
    assert "pad" not in tokens


def test_retriever_returns_relevant_passage(sample_passages):
    retriever = PaperRetriever(sample_passages)

    results = retriever.retrieve(
        "scaled dot product attention queries keys values",
        top_k=2,
    )

    assert len(results) > 0
    assert results[0]["passage_id"] == "attention_p4_c1"
    assert results[0]["score"] > 0


def test_retriever_returns_empty_for_unrelated_query(sample_passages):
    retriever = PaperRetriever(sample_passages)

    results = retriever.retrieve(
        "Kolkata weather forecast",
        top_k=5,
    )

    assert results == []


def test_retriever_respects_top_k(sample_passages):
    retriever = PaperRetriever(sample_passages)

    results = retriever.retrieve(
        "attention audio tokens",
        top_k=1,
    )

    assert len(results) <= 1


def test_retriever_rejects_empty_query(sample_passages):
    retriever = PaperRetriever(sample_passages)

    with pytest.raises(ValueError, match="Query cannot be empty"):
        retriever.retrieve("   ")


def test_retriever_rejects_invalid_top_k(sample_passages):
    retriever = PaperRetriever(sample_passages)

    with pytest.raises(ValueError, match="top_k must be at least 1"):
        retriever.retrieve("attention", top_k=0)


def test_retriever_rejects_empty_passage_collection():
    with pytest.raises(ValueError, match="No passages were provided"):
        PaperRetriever([])
