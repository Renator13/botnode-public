from datetime import datetime
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from jsonschema import Draft7Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field

VERSION = "0.1.0"
SERVICE_NAME = "law_v_api"
SCHEMA_REGISTRY: Dict[str, Dict[str, Any]] = {}
VALIDATION_STATS = {
    "total_validations": 0,
    "successful_validations": 0,
    "failed_validations": 0,
    "total_validation_time_ms": 0,
}

app = FastAPI(
    title="Law V API",
    description="BotNode's Schema-Enforced Settlement Verification Layer",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


class ValidationRequest(BaseModel):
    schema_id: str
    output_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    validation_time_ms: int
    schema_applied: str
    validation_id: str


class SchemaDefinition(BaseModel):
    schema_id: str
    schema_body: Dict[str, Any] = Field(..., alias="schema")
    skill_id: str
    version: str = "1.0.0"
    description: Optional[str] = None
    author: str = "BotNode Foundation"
    model_config = ConfigDict(populate_by_name=True)


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def register_schema(
    schema_id: str,
    schema: Dict[str, Any],
    skill_id: str,
    description: str,
    version: str = "1.0.0",
    author: str = "BotNode Foundation",
) -> None:
    SCHEMA_REGISTRY[schema_id] = {
        "schema_id": schema_id,
        "schema": schema,
        "skill_id": skill_id,
        "version": version,
        "description": description,
        "author": author,
        "created_at": utc_now(),
    }


def initialize_default_schemas() -> None:
    if SCHEMA_REGISTRY:
        return

    register_schema(
        schema_id="csv_parser_v1",
        skill_id="csv_parser",
        description="Schema for CSV parser outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["rows_processed", "columns", "errors", "summary"],
            "properties": {
                "rows_processed": {"type": "integer", "minimum": 0},
                "columns": {"type": "array", "items": {"type": "string"}},
                "errors": {"type": "array", "items": {"type": "string"}},
                "summary": {
                    "type": "object",
                    "required": ["total_rows", "valid_rows", "invalid_rows"],
                    "properties": {
                        "total_rows": {"type": "integer", "minimum": 0},
                        "valid_rows": {"type": "integer", "minimum": 0},
                        "invalid_rows": {"type": "integer", "minimum": 0},
                    },
                },
            },
        },
    )

    register_schema(
        schema_id="pdf_reader_v1",
        skill_id="pdf_reader",
        description="Schema for PDF reader outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["text", "metadata", "page_count"],
            "properties": {
                "text": {"type": "string"},
                "metadata": {"type": "object"},
                "page_count": {"type": "integer", "minimum": 1},
                "error": {"type": ["string", "null"]},
            },
        },
    )

    register_schema(
        schema_id="google_search_v1",
        skill_id="google_search",
        description="Schema for search outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["query", "results"],
            "properties": {
                "query": {"type": "string"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "url", "snippet"],
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string", "format": "uri"},
                            "snippet": {"type": "string"},
                            "rank": {"type": "integer", "minimum": 1},
                        },
                    },
                    "minItems": 0,
                },
                "total_results": {"type": "integer", "minimum": 0},
            },
        },
    )

    register_schema(
        schema_id="sentiment_analyzer_v1",
        skill_id="sentiment_analyzer",
        description="Schema for sentiment analyzer outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["sentiment_score", "sentiment_label", "confidence"],
            "properties": {
                "sentiment_score": {"type": "number", "minimum": -1, "maximum": 1},
                "sentiment_label": {
                    "type": "string",
                    "enum": ["negative", "neutral", "positive"],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "text_analyzed": {"type": "string"},
                "key_phrases": {"type": "array", "items": {"type": "string"}},
            },
        },
    )

    register_schema(
        schema_id="code_reviewer_v1",
        skill_id="code_reviewer",
        description="Schema for code reviewer outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["issues", "summary"],
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type", "severity", "message", "line"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "bug",
                                    "vulnerability",
                                    "style",
                                    "performance",
                                    "maintainability",
                                ],
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "high", "medium", "low", "info"],
                            },
                            "message": {"type": "string"},
                            "line": {"type": "integer", "minimum": 1},
                            "suggestion": {"type": "string"},
                        },
                    },
                },
                "summary": {"type": "object"},
                "code_language": {"type": "string"},
                "file_path": {"type": "string"},
            },
        },
    )

    register_schema(
        schema_id="text_summarizer_v1",
        skill_id="text_summarizer",
        description="Schema for text summarizer outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["summary", "original_length", "summary_length", "compression_ratio"],
            "properties": {
                "summary": {"type": "string"},
                "original_length": {"type": "integer", "minimum": 1},
                "summary_length": {"type": "integer", "minimum": 1},
                "compression_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                "key_points": {"type": "array", "items": {"type": "string"}},
                "readability_score": {"type": "number", "minimum": 0, "maximum": 100},
            },
        },
    )

    register_schema(
        schema_id="language_translator_v1",
        skill_id="language_translator",
        description="Schema for language translator outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["translated_text", "source_language", "target_language", "confidence"],
            "properties": {
                "translated_text": {"type": "string"},
                "source_language": {"type": "string"},
                "target_language": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "original_text": {"type": "string"},
                "detected_language": {"type": "string"},
                "translation_time_ms": {"type": "integer", "minimum": 0},
            },
        },
    )

    register_schema(
        schema_id="image_processor_v1",
        skill_id="image_processor",
        description="Schema for image processor outputs",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["processing_result", "image_metadata"],
            "properties": {
                "processing_result": {
                    "type": "object",
                    "required": ["success", "operation"],
                    "properties": {
                        "success": {"type": "boolean"},
                        "operation": {
                            "type": "string",
                            "enum": ["resize", "crop", "compress", "convert", "analyze"],
                        },
                        "output_format": {"type": "string"},
                        "output_size_bytes": {"type": "integer", "minimum": 0},
                        "processing_time_ms": {"type": "integer", "minimum": 0},
                    },
                },
                "image_metadata": {"type": "object"},
                "analysis_results": {"type": "object"},
                "error": {"type": ["string", "null"]},
            },
        },
    )


def record_validation(valid: bool, elapsed_ms: int) -> None:
    VALIDATION_STATS["total_validations"] += 1
    if valid:
        VALIDATION_STATS["successful_validations"] += 1
    else:
        VALIDATION_STATS["failed_validations"] += 1
    VALIDATION_STATS["total_validation_time_ms"] += elapsed_ms


@app.on_event("startup")
async def startup_event() -> None:
    initialize_default_schemas()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": VERSION,
        "schemas_registered": len(SCHEMA_REGISTRY),
        "validations_performed": VALIDATION_STATS["total_validations"],
        "timestamp": utc_now(),
    }


@app.get("/v1/schemas")
def list_schemas() -> Dict[str, Any]:
    schemas = [
        {
            "schema_id": entry["schema_id"],
            "skill_id": entry["skill_id"],
            "version": entry["version"],
            "description": entry["description"],
            "created_at": entry["created_at"],
        }
        for entry in sorted(SCHEMA_REGISTRY.values(), key=lambda item: item["schema_id"])
    ]
    return {"schemas": schemas, "total": len(schemas)}


@app.get("/v1/schemas/{schema_id}")
def get_schema(schema_id: str) -> Dict[str, Any]:
    entry = SCHEMA_REGISTRY.get(schema_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
    return entry


@app.post("/v1/validate", response_model=ValidationResponse)
def validate_output(request: ValidationRequest) -> ValidationResponse:
    schema_entry = SCHEMA_REGISTRY.get(request.schema_id)
    if not schema_entry:
        raise HTTPException(status_code=404, detail=f"Schema {request.schema_id} not found")

    start = time.perf_counter()
    validation_id = f"val_{uuid.uuid4().hex[:12]}"
    validator = Draft7Validator(schema_entry["schema"], format_checker=FormatChecker())

    errors: List[Dict[str, Any]] = []
    for error in sorted(validator.iter_errors(request.output_data), key=lambda e: list(e.path)):
        errors.append(
            {
                "field": ".".join(str(piece) for piece in error.path) or "root",
                "message": error.message,
                "code": "VALIDATION_ERROR",
            }
        )

    valid = not errors
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    record_validation(valid=valid, elapsed_ms=elapsed_ms)

    return ValidationResponse(
        valid=valid,
        errors=errors,
        validation_time_ms=elapsed_ms,
        schema_applied=request.schema_id,
        validation_id=validation_id,
    )


@app.get("/stats")
def stats() -> Dict[str, Any]:
    total_validations = VALIDATION_STATS["total_validations"]
    success_rate = (
        VALIDATION_STATS["successful_validations"] / total_validations
        if total_validations
        else 0.0
    )
    average_validation_time_ms = (
        VALIDATION_STATS["total_validation_time_ms"] / total_validations
        if total_validations
        else 0.0
    )
    return {
        "total_validations": total_validations,
        "successful_validations": VALIDATION_STATS["successful_validations"],
        "failed_validations": VALIDATION_STATS["failed_validations"],
        "success_rate": round(success_rate, 4),
        "average_validation_time_ms": round(average_validation_time_ms, 2),
        "schemas_count": len(SCHEMA_REGISTRY),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8110)
