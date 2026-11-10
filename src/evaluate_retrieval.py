
import csv
import json
import time
from pathlib import Path

from retriever import PaperRetriever


ROOT_DIR = Path(__file__).resolve().parents[1]

QUESTIONS_FILE = ROOT_DIR / "experiments" / "quality_questions.json"
OUTPUT_FILE = ROOT_DIR / "experiments" / "retrieval_comparison.csv"

TOP_K_VALUES = [3, 5, 8]


def main():
    with QUESTIONS_FILE.open("r", encoding="utf-8") as file:
        questions = json.load(file)

    retriever = PaperRetriever.from_json()

    results = []

    summaries = {
        top_k: {
            "supported_total": 0,
            "supported_hits": 0,
            "unsupported_total": 0,
            "unsupported_retrieved": 0,
            "retrieval_times": [],
        }
        for top_k in TOP_K_VALUES
    }

    for top_k in TOP_K_VALUES:
        print("\n" + "=" * 85)
        print(f"RETRIEVAL CONFIGURATION: TOP_K = {top_k}")
        print("=" * 85)

        for question in questions:
            question_id = question["id"]
            query = question["question"]
            expected_paper = question["expected_paper"]
            answerable = question["answerable"]

            start = time.perf_counter()
            passages = retriever.retrieve(query, top_k=top_k)
            retrieval_ms = (time.perf_counter() - start) * 1000

            summary = summaries[top_k]
            summary["retrieval_times"].append(retrieval_ms)

            if answerable:
                summary["supported_total"] += 1
            else:
                summary["unsupported_total"] += 1

            expected_found = False

            print(f"\n{question_id}: {query}")
            print(f"Expected paper: {expected_paper or 'None'}")
            print(f"Answerable: {answerable}")
            print(f"Retrieved passages: {len(passages)}")
            print(f"Retrieval time: {retrieval_ms:.3f} ms")

            if not passages:
                print("No passages retrieved.")

                results.append({
                    "top_k": top_k,
                    "question_id": question_id,
                    "question": query,
                    "answerable": answerable,
                    "expected_paper": expected_paper or "",
                    "rank": "",
                    "retrieved_paper": "",
                    "page_number": "",
                    "passage_id": "",
                    "score": "",
                    "expected_paper_match": False,
                    "retrieval_ms": round(retrieval_ms, 3),
                })

                continue

            for rank, passage in enumerate(passages, start=1):
                paper = passage["paper_title"]
                paper_match = (
                    expected_paper is not None
                    and paper == expected_paper
                )

                if paper_match:
                    expected_found = True

                results.append({
                    "top_k": top_k,
                    "question_id": question_id,
                    "question": query,
                    "answerable": answerable,
                    "expected_paper": expected_paper or "",
                    "rank": rank,
                    "retrieved_paper": paper,
                    "page_number": passage["page_number"],
                    "passage_id": passage["passage_id"],
                    "score": passage["score"],
                    "expected_paper_match": paper_match,
                    "retrieval_ms": round(retrieval_ms, 3),
                })

                print(
                    f"Rank {rank} | Score: {passage['score']:.4f} | "
                    f"Page: {passage['page_number']} | Paper: {paper}"
                )
                print(f"Passage ID: {passage['passage_id']}")

            if answerable:
                if expected_found:
                    summary["supported_hits"] += 1
                    print("Expected paper found.")
                else:
                    print("Expected paper NOT found.")

            elif passages:
                summary["unsupported_retrieved"] += 1
                print("Warning: passages retrieved for unsupported question.")

    fieldnames = [
        "top_k",
        "question_id",
        "question",
        "answerable",
        "expected_paper",
        "rank",
        "retrieved_paper",
        "page_number",
        "passage_id",
        "score",
        "expected_paper_match",
        "retrieval_ms",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 85)
    print("RETRIEVAL COMPARISON SUMMARY")
    print("=" * 85)

    for top_k in TOP_K_VALUES:
        summary = summaries[top_k]

        supported_total = summary["supported_total"]
        supported_hits = summary["supported_hits"]
        unsupported_total = summary["unsupported_total"]
        unsupported_retrieved = summary["unsupported_retrieved"]

        hit_rate = (
            supported_hits / supported_total * 100
            if supported_total else 0
        )

        average_retrieval_ms = (
            sum(summary["retrieval_times"])
            / len(summary["retrieval_times"])
            if summary["retrieval_times"] else 0
        )

        print(f"\nTOP_K = {top_k}")
        print(f"Supported questions: {supported_total}")
        print(f"Expected paper found: {supported_hits}")
        print(f"Expected-paper Hit@{top_k}: {hit_rate:.2f}%")
        print(
            f"Unsupported questions retrieving passages: "
            f"{unsupported_retrieved}/{unsupported_total}"
        )
        print(
            f"Average retrieval time: {average_retrieval_ms:.3f} ms"
        )

    print("\nDetailed comparison saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
