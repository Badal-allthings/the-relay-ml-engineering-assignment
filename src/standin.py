import asyncio
import os
import time
from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


RPM_LIMIT = int(os.getenv("STANDIN_RPM_LIMIT", "30"))
MAX_IN_FLIGHT = int(os.getenv("STANDIN_MAX_IN_FLIGHT", "5"))

request_times = deque()
active_requests = 0
state_lock = asyncio.Lock()

SAMPLE_ANSWER = (
    "This is a simulated response from the stand-in model service. "
    "It is intended for testing latency, streaming, failures, and load "
    "behaviour. It is not a real research answer."
)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    mode: str = "normal"
    stream: bool = False


app = FastAPI(title="The Relay Stand-in Model Service")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "stand-in",
        "rpm_limit": RPM_LIMIT,
        "max_in_flight": MAX_IN_FLIGHT,
    }


async def acquire_capacity():
    global active_requests

    async with state_lock:
        now = time.monotonic()

        while request_times and now - request_times[0] >= 60:
            request_times.popleft()

        if len(request_times) >= RPM_LIMIT:
            return False, "rate_limited"

        if active_requests >= MAX_IN_FLIGHT:
            return False, "concurrency_limited"

        request_times.append(now)
        active_requests += 1

    return True, "accepted"


async def release_capacity():
    global active_requests

    async with state_lock:
        active_requests -= 1


@app.post("/generate")
async def generate(request: GenerateRequest):
    request_id = str(uuid4())
    start = time.perf_counter()
    mode = request.mode.lower().strip()

    if mode not in {"normal", "slow", "timeout", "error"}:
        return JSONResponse(
            status_code=400,
            content={"request_id": request_id, "error": "Unknown mode"},
        )

    accepted, reason = await acquire_capacity()

    if not accepted:
        status_code = 429 if reason == "rate_limited" else 503
        return JSONResponse(
            status_code=status_code,
            content={
                "request_id": request_id,
                "status": reason,
                "error": "Stand-in capacity limit reached",
            },
        )

    if mode == "error":
        await asyncio.sleep(0.1)
        await release_capacity()

        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "status": "error",
                "error": "Simulated upstream service failure",
            },
        )

    if mode == "timeout":
        await asyncio.sleep(10)
    elif mode == "slow":
        await asyncio.sleep(2)
    else:
        async with state_lock:
            load = active_requests
        await asyncio.sleep(0.25 + (load - 1) * 0.10)

    if request.stream:

        async def stream_answer():
            try:
                words = SAMPLE_ANSWER.split()

                for index in range(0, len(words), 5):
                    yield " ".join(words[index:index + 5]) + " "
                    await asyncio.sleep(0.12)
            finally:
                await release_capacity()

        elapsed_ms = (time.perf_counter() - start) * 1000

        return StreamingResponse(
            stream_answer(),
            media_type="text/plain",
            headers={
                "X-Request-ID": request_id,
                "X-Standin-Status": "ok",
                "X-Elapsed-Before-Stream-Ms": str(round(elapsed_ms, 2)),
            },
        )

    try:
        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            "request_id": request_id,
            "status": "ok",
            "output": SAMPLE_ANSWER,
            "tokens_in_estimate": len(request.prompt.split()),
            "tokens_out_estimate": len(SAMPLE_ANSWER.split()),
            "total_ms": round(elapsed_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await release_capacity()