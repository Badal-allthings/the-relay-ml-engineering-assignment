
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
SOURCE_FILE = ROOT_DIR / "experiments" / "groq_load_results_v2.csv"
OUTPUT_FILE = ROOT_DIR / "experiments" / "groq_recovery_probe.csv"

load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL")

if not API_KEY or not MODEL:
    raise RuntimeError("Check GROQ_API_KEY and GROQ_MODEL in .env")


async def main():
    # Find the most recent rate-limited request in the benchmark.
    with SOURCE_FILE.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    limited_rows = [
        row for row in rows
        if row["status"] == "rate_limited"
    ]

    if not limited_rows:
        raise RuntimeError("No rate-limited request found in benchmark.")

    last_429 = max(
        datetime.fromisoformat(row["start_time"])
        for row in limited_rows
    )

    now = datetime.now().astimezone()
    elapsed = (now - last_429).total_seconds()

    # Ensure at least two seconds have elapsed since the last
    # rate-limited request started.
    wait_seconds = max(0, 2 - elapsed)

    print(f"Latest 429 request started: {last_429.isoformat()}")
    print(f"Elapsed since that request: {elapsed:.2f} seconds")
    print(f"Additional wait: {wait_seconds:.2f} seconds")

    if wait_seconds:
        await asyncio.sleep(wait_seconds)

    client = AsyncGroq(
        api_key=API_KEY,
        timeout=45.0,
        max_retries=0,
    )

    request_id = str(uuid4())
    start_time = datetime.now().astimezone().isoformat()
    start = time.perf_counter()

    status = "error"
    http_status = ""
    tokens_in = ""
    tokens_out = ""
    error_detail = ""

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Explain self-attention in one sentence."
                }
            ],
            max_completion_tokens=128,
            stream=False,
        )

        status = "ok"
        http_status = 200
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens

        print("\nRecovery probe succeeded.")
        print("Response:", response.choices[0].message.content)

    except Exception as error:
        http_status = getattr(error, "status_code", "")
        error_detail = str(error)[:500]

        if http_status == 429:
            status = "rate_limited"
        elif "timeout" in type(error).__name__.lower():
            status = "timeout"

        print("\nRecovery probe failed.")
        print(f"HTTP status: {http_status}")
        print(f"Error: {error_detail}")

    finally:
        total_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )
        await client.close()

    result = {
        "request_id": request_id,
        "last_429_start_time": last_429.isoformat(),
        "elapsed_before_probe_seconds": round(
            max(0, elapsed + wait_seconds), 2
        ),
        "start_time": start_time,
        "status": status,
        "http_status": http_status,
        "total_ms": total_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "error_detail": error_detail,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(result.keys()),
        )
        writer.writeheader()
        writer.writerow(result)

    print(f"\nSaved recovery result to: {OUTPUT_FILE}")
    print(f"Final status: {status}")
    print(f"Total latency: {total_ms} ms")


if __name__ == "__main__":
    asyncio.run(main())
