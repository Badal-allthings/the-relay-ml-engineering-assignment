import asyncio
import csv
import time
from datetime import datetime
from pathlib import Path

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT = ROOT_DIR / "experiments" / "standin_rpm_results.csv"
URL = "http://127.0.0.1:8000/generate"


async def main():
    results = []

    async with httpx.AsyncClient(timeout=5.0) as client:

        for number in range(1, 32):
            started_at = datetime.now().astimezone().isoformat()
            start = time.perf_counter()

            try:
                response = await client.post(
                    URL,
                    json={
                        "prompt": "Explain self-attention",
                        "mode": "normal",
                        "stream": False,
                    },
                )

                elapsed = round(
                    (time.perf_counter() - start) * 1000, 2
                )

                try:
                    data = response.json()
                except ValueError:
                    data = {}

                if response.status_code == 200:
                    status = "ok"
                elif response.status_code == 429:
                    status = "rate_limited"
                else:
                    status = "error"

                result = {
                    "request_number": number,
                    "start_time": started_at,
                    "http_status": response.status_code,
                    "status": status,
                    "total_ms": elapsed,
                    "error_detail": data.get("status", ""),
                }

            except httpx.TimeoutException:
                result = {
                    "request_number": number,
                    "start_time": started_at,
                    "http_status": "",
                    "status": "timeout",
                    "total_ms": "",
                    "error_detail": "client_timeout",
                }

            results.append(result)

            print(
                f"Request {number:02d}: "
                f"HTTP {result['http_status']} | "
                f"{result['status']} | "
                f"{result['total_ms']} ms"
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys(),
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n========== RPM TEST SUMMARY ==========")
    print(f"Total requests: {len(results)}")
    print(
        "Successful:",
        sum(row["status"] == "ok" for row in results),
    )
    print(
        "Rate limited:",
        sum(row["status"] == "rate_limited" for row in results),
    )
    print(f"Saved results to: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())