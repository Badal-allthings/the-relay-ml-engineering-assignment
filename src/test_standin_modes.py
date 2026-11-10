import asyncio
import csv
import time
from datetime import datetime
from pathlib import Path

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT = ROOT_DIR / "experiments" / "standin_modes_results.csv"
URL = "http://127.0.0.1:8000/generate"


async def run_mode_test(client, mode, stream=False, timeout=5.0):
    started_at = datetime.now().astimezone().isoformat()
    start = time.perf_counter()
    first_token_ms = ""
    output = ""

    try:
        if stream:
            async with client.stream(
                "POST",
                URL,
                json={
                    "prompt": "Explain self-attention",
                    "mode": mode,
                    "stream": True,
                },
                timeout=timeout,
            ) as response:
                status_code = response.status_code

                if status_code == 200:
                    async for chunk in response.aiter_text():
                        if chunk and first_token_ms == "":
                            first_token_ms = round(
                                (time.perf_counter() - start) * 1000, 2
                            )
                        output += chunk

        else:
            response = await client.post(
                URL,
                json={
                    "prompt": "Explain self-attention",
                    "mode": mode,
                    "stream": False,
                },
                timeout=timeout,
            )
            status_code = response.status_code
            output = response.text

        total_ms = round((time.perf_counter() - start) * 1000, 2)

        if status_code == 200:
            status = "ok"
        elif status_code == 429:
            status = "rate_limited"
        else:
            status = "error"

        detail = output[:250]

    except httpx.TimeoutException:
        total_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = ""
        status = "timeout"
        detail = "Client timeout"

    return {
        "mode": mode,
        "stream": stream,
        "start_time": started_at,
        "http_status": status_code,
        "status": status,
        "first_token_ms": first_token_ms,
        "total_ms": total_ms,
        "detail": detail,
    }


async def main():
    results = []

    async with httpx.AsyncClient() as client:
        tests = [
            ("normal", False, 5.0),
            ("slow", False, 5.0),
            ("error", False, 5.0),
            ("timeout", False, 1.0),
            ("normal", True, 5.0),
        ]

        for mode, stream, timeout in tests:
            print(f"Testing mode={mode}, stream={stream}")

            result = await run_mode_test(
                client,
                mode,
                stream=stream,
                timeout=timeout,
            )

            results.append(result)
            print(result)

            # Let the simulated 10-second timeout request finish server-side.
            if mode == "timeout":
                await asyncio.sleep(10)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys(),
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved {len(results)} observations to:")
    print(OUTPUT)


if __name__ == "__main__":
    asyncio.run(main())