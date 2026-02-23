from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
import uvicorn

from .engine import CodeReviewerEngine
from .models import CodeReviewInput, CodeReviewOutput


SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8080"))

app = FastAPI(title="code_reviewer_v1", version="0.1.0")
engine = CodeReviewerEngine()


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/run", response_model=CodeReviewOutput)
async def run_code_reviewer(payload: CodeReviewInput) -> CodeReviewOutput:
    try:
        return await engine.run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def main() -> None:
    uvicorn.run("code_reviewer_v1.api:app", host=SERVICE_HOST, port=SERVICE_PORT, reload=False)


if __name__ == "__main__":
    main()
