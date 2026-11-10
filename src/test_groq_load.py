
import asyncio
import csv
import os
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from groq import AsyncGroq


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT = ROOT_DIR / "experiments" / "groq_load_results_v2.csv"

load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL")

if not API_KEY or not MODEL:
    raise RuntimeError("Check GROQ_API_KEY and GROQ_MODEL in .env")


COLUMNS = [
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
    "http_status",
    "error_detail",
]

PROMPT = "Explain self-attention in one simple sentence."


async def send_request(client, scenario):
    request_id = str(uuid4())
    start_time = datetime.now().astimezone().isoformat()
    start = time.perf_counter()

    first_token_ms = ""
    total_ms = ""
    tokens_in = ""
    tokens_out = ""
    http_status = ""
    error_detail = ""
    status = "error"

    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": PROMPT}
            ],
            max_completion_tokens=256,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content

                # Time until first user-visible text.
                if content and first_token_ms == "":
                    first_token_ms = round(
                        (time.perf_counter() - start) * 1000,
                        2,
                    )

            if chunk.usage:
                tokens_in = chunk.usage.prompt_tokens
                tokens_out = chunk.usage.completion_tokens

        total_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )
        status = "ok"
        http_status = 200

    except Exception as error:
        total_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        http_status = getattr(error, "status_code", "")
        error_detail = str(error)[:500]

        if http_status == 429:
            status = "rate_limited"
        elif isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            status = "timeout"
        elif "timeout" in type(error).__name__.lower():
            status = "timeout"
        else:
            status = "error"

    return {
        "request_id": request_id,
        "scenario": scenario,
        "source": "real",
        "start_time": start_time,
        "first_token_ms": first_token_ms,
        "total_ms": total_ms,
        "status": status,
        "retries": 0,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "retrieval_setting": "direct_short_prompt_streaming",
        "answer_grade": "",
        "http_status": http_status,
        "error_detail": error_detail,
    }


async def run_steady(client):
    print("\nRunning steady traffic: 8 requests")

    results = []

    for _ in range(8):
        results.append(
            await send_request(client, "steady")
        )
        await asyncio.sleep(0.6)

    return results


async def run_burst(client):
    print("\nRunning burst traffic: 12 simultaneous requests")

    tasks = [
        send_request(client, "burst")
        for _ in range(12)
    ]

    return await asyncio.gather(*tasks)


async def run_overload(client):
    print("\nRunning sustained overload: 20 simultaneous requests")

    tasks = [
        send_request(client, "sustained_overload")
        for _ in range(20)
    ]

    return await asyncio.gather(*tasks)


def save_results(results):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=COLUMNS,
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved {len(results)} rows to:")
    print(OUTPUT)


def print_summary(results):
    print("\n========== GROQ LOAD TEST SUMMARY ==========")

    for scenario in [
        "steady",
        "burst",
        "sustained_overload",
    ]:
        rows = [
            row for row in results
            if row["scenario"] == scenario
        ]

        outcomes = {}

        for row in rows:
            outcomes[row["status"]] = (
                outcomes.get(row["status"], 0) + 1
            )

        successful = [
            float(row["total_ms"])
            for row in rows
            if row["status"] == "ok"
            and row["total_ms"] != ""
        ]

        first_text = [
            float(row["first_token_ms"])
            for row in rows
            if row["status"] == "ok"
            and row["first_token_ms"] != ""
        ]

        print(f"\nScenario: {scenario}")
        print(f"Requests: {len(rows)}")
        print(f"Outcomes: {outcomes}")

        if successful:
            print(
                f"Average total latency: "
                f"{sum(successful) / len(successful):.2f} ms"
            )

        if first_text:
            print(
                f"Average first-text latency: "
                f"{sum(first_text) / len(first_text):.2f} ms"
            )

        print(
            f"First-text timings recorded: "
            f"{len(first_text)}/{len(successful)} successful requests"
        )

        for row in rows:
            if row["status"] != "ok":
                print(
                    f"Failure: HTTP {row['http_status']} | "
                    f"{row['status']} | "
                    f"{row['error_detail'][:150]}"
                )


async def main():
    print(f"Groq model: {MODEL}")
    print("Retries: disabled (0)")
    print("Maximum completion tokens: 256")
    print("Total planned requests: 40")

    client = AsyncGroq(
        api_key=API_KEY,
        timeout=45.0,
        max_retries=0,
    )

    try:
        all_results = []

        all_results.extend(
            await run_steady(client)
        )

        all_results.extend(
            await run_burst(client)
        )

        all_results.extend(
            await run_overload(client)
        )

        save_results(all_results)
        print_summary(all_results)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
