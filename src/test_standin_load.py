import asyncio
import csv
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]

# Save separately. Do not overwrite the first experiment.
RESULTS_FILE = ROOT_DIR / "experiments" / "standin_load_results_v2.csv"

URL = "http://127.0.0.1:8000/generate"

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


async def send_request(
    client: httpx.AsyncClient,
    scenario: str,
) -> dict:
    request_id = str(uuid4())
    start_time = datetime.now().astimezone().isoformat()
    start = time.perf_counter()

    row = {
        "request_id": request_id,
        "scenario": scenario,
        "source": "stand-in",
        "start_time": start_time,
        "first_token_ms": "",
        "total_ms": "",
        "status": "error",
        "retries": 0,
        "tokens_in": "",
        "tokens_out": "",
        "retrieval_setting": "standin_normal",
        "answer_grade": "",
        "http_status": "",
        "error_detail": "",
    }

    try:
        response = await client.post(
            URL,
            json={
                "prompt": "Explain self-attention in a Transformer.",
                "mode": "normal",
                "stream": False,
            },
        )

        row["total_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )
        row["http_status"] = response.status_code

        try:
            data = response.json()
        except ValueError:
            data = {}

        row["request_id"] = data.get(
            "request_id",
            response.headers.get("X-Request-ID", request_id),
        )

        if response.status_code == 200:
            row["status"] = "ok"
            row["tokens_in"] = data.get("tokens_in_estimate", "")
            row["tokens_out"] = data.get("tokens_out_estimate", "")

        elif response.status_code == 429:
            row["status"] = "rate_limited"
            row["error_detail"] = data.get("status", "rate_limited")

        elif response.status_code == 503:
            row["status"] = "error"
            row["error_detail"] = data.get(
                "status",
                data.get("error", "service_unavailable"),
            )

        else:
            row["status"] = "error"
            row["error_detail"] = data.get(
                "error",
                f"http_{response.status_code}",
            )

    except httpx.TimeoutException:
        row["total_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )
        row["status"] = "timeout"
        row["error_detail"] = "client_timeout"

    except httpx.RequestError as error:
        row["total_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )
        row["status"] = "error"
        row["error_detail"] = type(error).__name__

    return row


async def run_steady(client):
    print("\nRunning steady traffic: 8 requests, spaced 0.6 seconds apart")

    results = []

    for _ in range(8):
        results.append(await send_request(client, "steady"))
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
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with RESULTS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved {len(results)} rows to:")
    print(RESULTS_FILE)


def print_summary(results):
    print("\n========== LOAD TEST SUMMARY ==========")

    for scenario in ["steady", "burst", "sustained_overload"]:
        scenario_rows = [
            row for row in results
            if row["scenario"] == scenario
        ]

        counts = {}

        for row in scenario_rows:
            status = row["status"]
            counts[status] = counts.get(status, 0) + 1

        details = {}

        for row in scenario_rows:
            detail = row["error_detail"]

            if detail:
                details[detail] = details.get(detail, 0) + 1

        successful_times = [
            float(row["total_ms"])
            for row in scenario_rows
            if row["status"] == "ok" and row["total_ms"] != ""
        ]

        print(f"\nScenario: {scenario}")
        print(f"Requests: {len(scenario_rows)}")
        print(f"Outcomes: {counts}")
        print(f"Error details: {details}")

        if successful_times:
            print(
                "Successful average latency: "
                f"{sum(successful_times) / len(successful_times):.2f} ms"
            )


async def main():
    timeout = httpx.Timeout(5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        all_results = []

        all_results.extend(await run_steady(client))
        all_results.extend(await run_burst(client))
        all_results.extend(await run_overload(client))

    save_results(all_results)
    print_summary(all_results)


if __name__ == "__main__":
    asyncio.run(main())