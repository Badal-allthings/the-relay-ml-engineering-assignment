
import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


PASSAGES_FILE = Path("data/passages.json")


STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were",
    "what", "how", "why", "when", "where", "who",
    "of", "in", "on", "at", "to", "for", "from",
    "by", "with", "and", "or", "but", "as", "it",
    "this", "that", "these", "those", "does", "do",
    "did", "can", "could", "would", "should",
    "i", "we", "you", "they", "he", "she"
}


def tokenize(text: str) -> list[str]:
    """Convert text into lowercase tokens, excluding common words and PDF artefacts."""
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())

    return [
        token for token in tokens
        if token not in STOPWORDS
        and token not in {"eos", "pad"}
    ]

class PaperRetriever:
    def __init__(self, passages: list[dict]):
        if not passages:
            raise ValueError("No passages were provided.")

        self.passages = passages
        self.tokenized_corpus = [
            tokenize(passage["text"]) for passage in passages
        ]

        self.bm25 = BM25Okapi(self.tokenized_corpus)

    @classmethod
    def from_json(cls, file_path: Path = PASSAGES_FILE):
        with file_path.open("r", encoding="utf-8") as file:
            passages = json.load(file)

        return cls(passages)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        if not query.strip():
            raise ValueError("Query cannot be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # No lexical evidence was found in the corpus.
        if not any(score > 0 for score in scores):
            return []

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )

        results = []

        for index in ranked_indices:
            # Ignore passages with no lexical match.
            if scores[index] <= 0:
                break

            passage = self.passages[index]

            results.append({
                **passage,
                "score": round(float(scores[index]), 4),
            })

            if len(results) >= top_k:
                break

        return results


def main():
    retriever = PaperRetriever.from_json()

    query = "How does self-attention work in the Transformer?"

    results = retriever.retrieve(query, top_k=5)

    print(f"\nQuestion: {query}")
    print(f"\nTop {len(results)} retrieved passages:\n")

    for rank, result in enumerate(results, start=1):
        print(f"Rank: {rank}")
        print(f"Paper: {result['paper_title']}")
        print(f"Page: {result['page_number']}")
        print(f"Score: {result['score']}")
        print(f"Passage ID: {result['passage_id']}")
        print(f"Text: {result['text'][:400]}...")
        print("-" * 70)


if __name__ == "__main__":
    main()
