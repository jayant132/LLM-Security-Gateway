import logging
import time
import json

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.guardrails import check_input, check_output
from app.llm_client import generate
from app.metrics import REQUESTS_TOTAL, BLOCKED_INPUT_TOTAL, OUTPUT_REDACTIONS_TOTAL, REQUEST_LATENCY

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gateway")

app = FastAPI(title="LLM Security Gateway")


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str
    blocked: bool
    guardrail_events: list


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()
    REQUESTS_TOTAL.inc()
    events = []

    blocked, in_reasons = check_input(req.prompt)
    events.extend(in_reasons)
    for r in in_reasons:
        BLOCKED_INPUT_TOTAL.labels(category=r["category"], source=r["source"]).inc()

    if blocked:
        latency = time.time() - start
        REQUEST_LATENCY.observe(latency)
        log.info(json.dumps({"event": "input_blocked", "reasons": in_reasons, "latency": latency}))
        return ChatResponse(response="Request blocked by guardrails.", blocked=True, guardrail_events=events)

    raw_output = generate(req.prompt)
    redacted_output, out_reasons = check_output(raw_output)
    events.extend(out_reasons)
    for r in out_reasons:
        OUTPUT_REDACTIONS_TOTAL.labels(category=r["category"]).inc()

    latency = time.time() - start
    REQUEST_LATENCY.observe(latency)
    log.info(json.dumps({"event": "request_completed", "reasons": events, "latency": latency}))

    return ChatResponse(response=redacted_output, blocked=False, guardrail_events=events)
