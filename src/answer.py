
import csv
import json
import time
from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from retriever import PaperRetriever


ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")

RESULTS_FILE = ROOT_DIR / "results.csv"
QUALITY_ANSWERS_FILE = ROOT_DIR / "experiments" / "quality_answers.jsonl"

REFUSAL_MESSAGE = "I cannot answer this question from the available papers."


def log_result(
    request_id: str,
    start_time: str,
    total_ms: float,
    status: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    top_k: int = 5,
    answer_grade: str = "",
):
    """Append one result using the required 12-column CSV format."""

    file_exists = RESULTS_FILE.exists()

    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "request_id",
                "scenario",
                "source",
                "start_time",
                "first_token_ms",
                "total_ms",
                "status",
                "retries",
                "tokens_in",
                "tokens_out",
                "retrieval_setting",
                "answer_grade",
            ])

        writer.writerow([
            request_id,
            "quality",
            "real",
            start_time,
            "",
            round(total_ms, 2),
            status,
            0,
            tokens_in,
            tokens_out,
            f"BM25_top{top_k}_char1200_overlap150",
            answer_grade,
        ])


def save_quality_answer(
    question_id: str,
    request_id: str,
    question: str,
    answer: str,
    status: str,
    passages: list[dict],
    finish_reason: str = "",
    error: str = "",
):
    """Save the question, answer, and retrieved evidence for manual review."""

    QUALITY_ANSWERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "question_id": question_id,
        "request_id": request_id,
        "question": question,
        "answer": answer,
        "status": status,
        "finish_reason": finish_reason,
        "error": error,
        "retrieved_passages": [
            {
                "paper_title": passage["paper_title"],
                "page_number": passage["page_number"],
                "passage_id": passage["passage_id"],
                "score": passage.get("score"),
            }
            for passage in passages
        ],
        "saved_at": datetime.now().astimezone().isoformat(),
    }

    with QUALITY_ANSWERS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_context(passages: list[dict]) -> str:
    """Format retrieved passages with their citation metadata."""

    context_parts = []

    for index, passage in enumerate(passages, start=1):
        context_parts.append(
            f"""
SOURCE {index}
Paper: {passage['paper_title']}
PDF page: {passage['page_number']}
Passage ID: {passage['passage_id']}
Content:
{passage['text']}
"""
        )

    return "\n".join(context_parts)


def answer_question(
    question: str,
    top_k: int = 5,
    question_id: str = "MANUAL",
) -> str:
    """Retrieve research passages and generate a cited answer."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not question_id.strip():
        question_id = "MANUAL"

    request_id = (
        f"{question_id}-REQ-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    )
    request_start_time = datetime.now().astimezone().isoformat()

    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if not api_key or not model:
        raise RuntimeError("Check GROQ_API_KEY and GROQ_MODEL in .env")

    retriever = PaperRetriever.from_json()
    passages = retriever.retrieve(question, top_k=top_k)

    # No evidence was retrieved, so do not send a request to Groq.
    if not passages:
        answer = REFUSAL_MESSAGE

        log_result(
            request_id=request_id,
            start_time=request_start_time,
            total_ms=0,
            status="ok",
            top_k=top_k,
        )

        save_quality_answer(
            question_id=question_id,
            request_id=request_id,
            question=question,
            answer=answer,
            status="refused_no_passages",
            passages=[],
        )

        print("No relevant passages retrieved. Refusing to answer.")
        print("Request ID:", request_id)

        return answer

    context = build_context(passages)

    client = Groq(api_key=api_key)

    request_started = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """

You are a research assistant answering questions using only
the supplied passages from three research papers.

GENERAL RULES:
1. Use only information explicitly supported by the retrieved passages.
2. Do not use outside knowledge or invent facts.
3. Cite every factual and technical claim using this format:
   [Paper title, PDF page X]
4. Use the exact paper title and PDF page number provided.
5. If the passages do not contain enough evidence, clearly say:
   "I cannot answer this question from the available papers."
6. If only part of the question is supported, answer that part
   and clearly identify what cannot be established.
7. Be concise and explain technical ideas clearly.
8. Place citations immediately after the sentence containing
   the supported claim, not only at the end of the answer.

9. When explaining an equation, cite the passage that contains
   or explains that equation.

10. When describing queries, keys, and values, cite the passages
    that explain their roles.

11. Do not present general technical knowledge as if it came
    from the retrieved papers.

12. If a technical explanation is not directly supported by
    the retrieved passages, qualify it or omit it.
13. Cite each numbered step or bullet independently when it
    contains a technical claim.

14. Do not claim that a paper illustrates or demonstrates
    something unless the retrieved passage explicitly supports it.

15. Keep mathematical equations properly formatted using
    balanced LaTeX delimiters.

16. Avoid repeating the same citation at the end if all claims
    already have appropriate inline citations.

CITATION AND EVIDENCE RULES:
- Every technical claim must have an inline citation.
- Use only the retrieved passages as evidence.
- Cite the exact PDF page number provided in the passage metadata.
- Do not cite a page unless the retrieved passage from that page supports the claim.
- If the retrieved passages do not contain enough evidence, explicitly say what cannot be established.
- Never invent equations, page numbers, or paper details.

"""
                },
                {
                    "role": "user",
                    "content": f"""
Question:
{question}

Retrieved research passages:
{context}

Answer using the instructions above.
"""
                }
            ],
            max_completion_tokens=1800,
            temperature=0,
        )

    except Exception as error:
        total_ms = (time.perf_counter() - request_started) * 1000

        log_result(
            request_id=request_id,
            start_time=request_start_time,
            total_ms=total_ms,
            status="error",
            top_k=top_k,
        )

        save_quality_answer(
            question_id=question_id,
            request_id=request_id,
            question=question,
            answer="",
            status="error",
            passages=passages,
            error=str(error),
        )

        raise

    total_ms = (time.perf_counter() - request_started) * 1000

    tokens_in = 0
    tokens_out = 0

    if response.usage:
        tokens_in = response.usage.prompt_tokens or 0
        tokens_out = response.usage.completion_tokens or 0

    answer = response.choices[0].message.content or ""
    finish_reason = response.choices[0].finish_reason or ""

    log_result(
        request_id=request_id,
        start_time=request_start_time,
        total_ms=total_ms,
        status="ok",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        top_k=top_k,
    )

    save_quality_answer(
        question_id=question_id,
        request_id=request_id,
        question=question,
        answer=answer.strip(),
        status="ok" if answer.strip() else "empty_response",
        passages=passages,
        finish_reason=finish_reason,
    )

    print("\n--- API Response Metadata ---")
    print("Question ID:", question_id)
    print("Request ID:", request_id)
    print("Finish reason:", finish_reason)
    print(f"Total API response time: {total_ms:.2f} ms")
    print("Input tokens:", tokens_in)
    print("Output tokens:", tokens_out)
    print("Saved answer:", QUALITY_ANSWERS_FILE)

    if not answer.strip():
        return "The model returned an empty response."

    return answer.strip()


def main():
    question_id = input("\nEnter question ID (e.g. Q01): ").strip()
    question = input("Enter your research question: ").strip()

    print("\nGenerating answer...\n")

    answer = answer_question(
        question=question,
        top_k=5,
        question_id=question_id or "MANUAL",
    )

    print("=" * 70)
    print("RESEARCH ASSISTANT ANSWER")
    print("=" * 70)
    print(answer)
    print("=" * 70)


if __name__ == "__main__":
    main()
