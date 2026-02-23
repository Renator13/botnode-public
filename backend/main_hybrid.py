from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

VERSION = "0.1.0"
SERVICE_NAME = "botnode_hybrid_api"


def load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_file(".env.hybrid")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
LAW_V_API_URL = os.getenv("LAW_V_API_URL", "http://localhost:8110").rstrip("/")
CRI_API_URL = os.getenv("CRI_API_URL", "http://localhost:8111").rstrip("/")
ENABLE_LAW_V = os.getenv("ENABLE_LAW_V", "true").lower() in {"1", "true", "yes", "on"}

HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "3"))
CLIENT_TIMEOUT = httpx.Timeout(timeout=HTTP_TIMEOUT_SECONDS)

SCHEMA_MAP = {
    "csv_parser": "csv_parser_v1",
    "pdf_reader": "pdf_reader_v1",
    "google_search": "google_search_v1",
    "sentiment_analyzer": "sentiment_analyzer_v1",
    "code_reviewer": "code_reviewer_v1",
    "text_summarizer": "text_summarizer_v1",
    "language_translator": "language_translator_v1",
    "image_processor": "image_processor_v1",
}

DEFAULT_SKILLS: List[Dict[str, Any]] = [
    {"skill_id": "csv_parser", "port": 8001},
    {"skill_id": "pdf_reader", "port": 8002},
    {"skill_id": "google_search", "port": 8003},
    {"skill_id": "sentiment_analyzer", "port": 8004},
    {"skill_id": "code_reviewer", "port": 8005},
    {"skill_id": "performance_analyzer", "port": 8036},
    {"skill_id": "compliance_checker", "port": 8037},
    {"skill_id": "document_reporter", "port": 8039},
    {"skill_id": "gus_social_manager", "port": 9001},
    {"skill_id": "gus_email_handler", "port": 9002},
    {"skill_id": "gus_discord_bot", "port": 9003},
]

app = FastAPI(
    title="BotNode Hybrid API",
    description="BotNode Foundation + Trust Layer (Law V + CRI)",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


class SkillExecuteRequest(BaseModel):
    skill_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    node_id: Optional[str] = None
    transaction_id: Optional[str] = None
    validate_output: bool = True


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def request_json(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    try:
        with httpx.Client(timeout=CLIENT_TIMEOUT) as client:
            response = client.request(method=method, url=url, json=payload, params=params)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Upstream unavailable: {exc}") from exc

    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}
    return response.status_code, data


def try_request_json(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    try:
        return request_json(method=method, url=url, payload=payload, params=params)
    except HTTPException:
        return None, None


def make_fallback_output(skill_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if skill_id == "csv_parser":
        rows = int(parameters.get("rows", 10))
        return {
            "rows_processed": rows,
            "columns": parameters.get("columns", ["id", "name"]),
            "errors": [],
            "summary": {"total_rows": rows, "valid_rows": rows, "invalid_rows": 0},
        }
    if skill_id == "sentiment_analyzer":
        text = str(parameters.get("text", ""))
        return {
            "sentiment_score": 0.1,
            "sentiment_label": "neutral",
            "confidence": 0.7,
            "text_analyzed": text,
            "key_phrases": [],
        }
    return {
        "status": "simulated",
        "skill_id": skill_id,
        "parameters": parameters,
        "generated_at": utc_now(),
    }


def proxy_or_error(method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    status, data = request_json(method=method, url=url, payload=payload)
    if status >= 400:
        detail = data.get("detail", data)
        raise HTTPException(status_code=status, detail=detail)
    return data


def run_law_v_validation(schema_id: str, output_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    payload = {"schema_id": schema_id, "output_data": output_data, "metadata": metadata}
    return proxy_or_error("POST", f"{LAW_V_API_URL}/v1/validate", payload=payload)


def update_cri(
    node_id: str,
    transaction_id: str,
    success: bool,
    skill_id: str,
    validation_passed: bool,
) -> Dict[str, Any]:
    payload = {
        "node_id": node_id,
        "transaction_id": transaction_id,
        "success": success,
        "skill_id": skill_id,
        "validation_passed": validation_passed,
    }
    return proxy_or_error("POST", f"{CRI_API_URL}/v1/cri/update", payload=payload)


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "mode": "hybrid",
        "enable_law_v": ENABLE_LAW_V,
        "timestamp": utc_now(),
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    backend_status, _ = try_request_json("GET", f"{BACKEND_URL}/health")
    law_v_status, law_v_data = try_request_json("GET", f"{LAW_V_API_URL}/health")
    cri_status, cri_data = try_request_json("GET", f"{CRI_API_URL}/health")

    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": VERSION,
        "components": {
            "backend": {
                "url": BACKEND_URL,
                "reachable": backend_status is not None and backend_status < 500,
                "status_code": backend_status,
            },
            "law_v": {
                "url": LAW_V_API_URL,
                "reachable": law_v_status is not None and law_v_status < 500,
                "status_code": law_v_status,
                "schemas_registered": (law_v_data or {}).get("schemas_registered"),
            },
            "cri": {
                "url": CRI_API_URL,
                "reachable": cri_status is not None and cri_status < 500,
                "status_code": cri_status,
                "nodes_registered": (cri_data or {}).get("nodes_registered"),
            },
        },
        "timestamp": utc_now(),
    }


@app.get("/api/v1/skills")
def list_skills() -> Dict[str, Any]:
    backend_status, data = try_request_json("GET", f"{BACKEND_URL}/api/v1/skills")
    if backend_status is not None and backend_status < 400 and isinstance(data, dict):
        return data
    return {"skills": DEFAULT_SKILLS, "total": len(DEFAULT_SKILLS), "source": "fallback"}


@app.post("/api/v1/skills/execute")
def execute_skill(request: SkillExecuteRequest) -> Dict[str, Any]:
    backend_payload = {"skill_id": request.skill_id, "parameters": request.parameters}
    backend_status, backend_data = try_request_json(
        "POST",
        f"{BACKEND_URL}/api/v1/skills/execute",
        payload=backend_payload,
    )

    used_fallback = not (backend_status is not None and backend_status < 400 and isinstance(backend_data, dict))
    if used_fallback:
        execution_output = make_fallback_output(request.skill_id, request.parameters)
        base_response = {
            "job_id": request.transaction_id or f"job_{uuid4().hex[:12]}",
            "skill_id": request.skill_id,
            "status": "completed",
            "output": execution_output,
            "source": "fallback",
        }
    else:
        base_response = backend_data
        execution_output = (
            backend_data.get("output")
            or backend_data.get("result")
            or backend_data.get("data")
            or {}
        )

    trust_block: Dict[str, Any] = {"law_v_enabled": ENABLE_LAW_V, "validated": False}
    if ENABLE_LAW_V and request.validate_output:
        schema_id = SCHEMA_MAP.get(request.skill_id)
        if schema_id and isinstance(execution_output, dict):
            metadata = {
                "node_id": request.node_id or "node_local_hybrid",
                "transaction_id": request.transaction_id or base_response.get("job_id"),
            }
            validation_result = run_law_v_validation(
                schema_id=schema_id,
                output_data=execution_output,
                metadata=metadata,
            )
            trust_block["validation"] = validation_result
            trust_block["validated"] = True

            node_id = metadata["node_id"]
            tx_id = str(metadata["transaction_id"] or f"tx_{uuid4().hex[:12]}")
            cri_result = update_cri(
                node_id=node_id,
                transaction_id=tx_id,
                success=bool(validation_result.get("valid")),
                skill_id=request.skill_id,
                validation_passed=bool(validation_result.get("valid")),
            )
            trust_block["cri_update"] = cri_result
        else:
            trust_block["reason"] = "No schema mapping or output not an object"

    base_response["trust"] = trust_block
    return base_response


@app.get("/api/v1/trust/health")
def trust_health() -> Dict[str, Any]:
    law_v_status, law_v_data = try_request_json("GET", f"{LAW_V_API_URL}/health")
    cri_status, cri_data = try_request_json("GET", f"{CRI_API_URL}/health")
    return {
        "status": "healthy" if law_v_status == 200 and cri_status == 200 else "degraded",
        "law_v": {"status_code": law_v_status, "data": law_v_data},
        "cri": {"status_code": cri_status, "data": cri_data},
        "timestamp": utc_now(),
    }


@app.post("/api/v1/trust/validate")
def trust_validate(request: Dict[str, Any]) -> Dict[str, Any]:
    return proxy_or_error("POST", f"{LAW_V_API_URL}/v1/validate", payload=request)


@app.get("/api/v1/trust/cri/{node_id}")
def trust_cri(node_id: str) -> Dict[str, Any]:
    return proxy_or_error("GET", f"{CRI_API_URL}/v1/cri/{node_id}")


@app.get("/api/v1/trust/schemas")
def trust_schemas() -> Dict[str, Any]:
    return proxy_or_error("GET", f"{LAW_V_API_URL}/v1/schemas")


@app.get("/api/v1/trust/stats")
def trust_stats() -> Dict[str, Any]:
    law_v = proxy_or_error("GET", f"{LAW_V_API_URL}/stats")
    cri = proxy_or_error("GET", f"{CRI_API_URL}/stats")
    return {"law_v": law_v, "cri": cri, "timestamp": utc_now()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100)
