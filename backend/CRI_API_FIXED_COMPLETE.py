from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel, Field

VERSION = "0.1.0"
SERVICE_NAME = "cri_api"
GENESIS_SCORE = 1.0


@dataclass
class CRIHistoryEntry:
    timestamp: str
    old_score: float
    new_score: float
    change: float
    reason: str
    transaction_id: Optional[str] = None


@dataclass
class NodeCRI:
    node_id: str
    current_score: float
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    success_rate: float
    last_active: str
    capabilities: List[str]
    calibration_scores: Dict[str, float]
    history: List[CRIHistoryEntry]
    created_at: str


class CRIResponse(BaseModel):
    node_id: str
    cri_score: float = Field(..., ge=0.0, le=5.0, description="Current CRI score (0-5)")
    total_transactions: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    last_active: str
    capabilities: List[str] = Field(default_factory=list)
    calibration_scores: Dict[str, float] = Field(default_factory=dict)


class TransactionEvent(BaseModel):
    node_id: str
    transaction_id: str
    success: bool
    skill_id: str
    validation_passed: Optional[bool] = True
    calibration_test: Optional[bool] = False
    test_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class CRIHistoryResponse(BaseModel):
    node_id: str
    history: List[Dict[str, Any]]
    total_entries: int


app = FastAPI(
    title="CRI API",
    description="BotNode's Confidence Reputation Index - The FICO of the Agentic Web",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

NODE_REGISTRY: Dict[str, NodeCRI] = {}


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def clamp_score(score: float) -> float:
    return max(0.0, min(score, 5.0))


def create_genesis_node(node_id: str, now: Optional[str] = None) -> NodeCRI:
    timestamp = now or utc_now()
    return NodeCRI(
        node_id=node_id,
        current_score=GENESIS_SCORE,
        total_transactions=0,
        successful_transactions=0,
        failed_transactions=0,
        success_rate=0.0,
        last_active=timestamp,
        capabilities=[],
        calibration_scores={},
        history=[],
        created_at=timestamp,
    )


def calculate_cri_update(
    old_score: float,
    event_type: str,
    success: bool = True,
    test_score: Optional[float] = None,
) -> Tuple[float, float]:
    if event_type == "transaction":
        delta = 0.05 if success else -0.20
    elif event_type == "timeout":
        delta = -0.30
    elif event_type == "calibration":
        if test_score is None:
            delta = 0.0
        else:
            delta = min(0.05 + (test_score * 0.10), 0.15)
    else:
        delta = 0.0

    new_score = clamp_score(old_score + delta)
    return round(new_score, 4), round(new_score - old_score, 4)


def event_type_for(event: TransactionEvent) -> str:
    if event.calibration_test:
        return "calibration"
    if event.success:
        return "transaction"
    if event.validation_passed is False:
        return "transaction"
    return "timeout"


def update_success_rate(node: NodeCRI) -> None:
    if node.total_transactions > 0:
        node.success_rate = node.successful_transactions / node.total_transactions
    else:
        node.success_rate = 0.0


def history_reason(event: TransactionEvent, event_type: str) -> str:
    if event_type == "calibration":
        if event.test_score is None:
            return f"Calibration test for {event.skill_id}"
        return f"Calibration test for {event.skill_id} (score={event.test_score:.2f})"
    if event_type == "timeout":
        return f"Timeout during {event.skill_id} transaction"
    if event.success:
        return f"Successful {event.skill_id} transaction"
    return f"Failed {event.skill_id} transaction (validation failed)"


def calibration_tests_count() -> int:
    total = 0
    for node in NODE_REGISTRY.values():
        for entry in node.history:
            if entry.reason.startswith("Calibration test"):
                total += 1
    return total


def initialize_test_data() -> None:
    if NODE_REGISTRY:
        return

    now = datetime.utcnow()

    node_alpha = NodeCRI(
        node_id="node_alpha_123",
        current_score=4.2,
        total_transactions=150,
        successful_transactions=142,
        failed_transactions=8,
        success_rate=142 / 150,
        last_active=(now - timedelta(minutes=30)).replace(microsecond=0).isoformat() + "Z",
        capabilities=["csv_parser", "pdf_reader", "sentiment_analyzer"],
        calibration_scores={
            "csv_parser": 0.95,
            "pdf_reader": 0.88,
            "sentiment_analyzer": 0.92,
        },
        history=[
            CRIHistoryEntry(
                timestamp=(now - timedelta(days=1)).replace(microsecond=0).isoformat() + "Z",
                old_score=4.1,
                new_score=4.2,
                change=0.1,
                reason="Successful csv_parser transaction",
                transaction_id="tx_001",
            )
        ],
        created_at=(now - timedelta(days=30)).replace(microsecond=0).isoformat() + "Z",
    )

    node_beta = NodeCRI(
        node_id="node_beta_456",
        current_score=2.8,
        total_transactions=45,
        successful_transactions=38,
        failed_transactions=7,
        success_rate=38 / 45,
        last_active=(now - timedelta(hours=2)).replace(microsecond=0).isoformat() + "Z",
        capabilities=["google_search", "code_reviewer"],
        calibration_scores={"google_search": 0.75, "code_reviewer": 0.82},
        history=[],
        created_at=(now - timedelta(days=15)).replace(microsecond=0).isoformat() + "Z",
    )

    node_gamma = NodeCRI(
        node_id="node_gamma_789",
        current_score=1.0,
        total_transactions=0,
        successful_transactions=0,
        failed_transactions=0,
        success_rate=0.0,
        last_active=now.replace(microsecond=0).isoformat() + "Z",
        capabilities=[],
        calibration_scores={},
        history=[],
        created_at=now.replace(microsecond=0).isoformat() + "Z",
    )

    NODE_REGISTRY[node_alpha.node_id] = node_alpha
    NODE_REGISTRY[node_beta.node_id] = node_beta
    NODE_REGISTRY[node_gamma.node_id] = node_gamma


@app.on_event("startup")
async def startup_event() -> None:
    initialize_test_data()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": VERSION,
        "nodes_registered": len(NODE_REGISTRY),
        "calibration_tests": calibration_tests_count(),
        "timestamp": utc_now(),
    }


@app.get("/v1/cri/{node_id}", response_model=CRIResponse)
def get_cri(node_id: str) -> CRIResponse:
    node = NODE_REGISTRY.get(node_id)
    if node is None:
        node = create_genesis_node(node_id)
    return CRIResponse(
        node_id=node.node_id,
        cri_score=round(node.current_score, 4),
        total_transactions=node.total_transactions,
        success_rate=round(node.success_rate, 4),
        last_active=node.last_active,
        capabilities=node.capabilities,
        calibration_scores=node.calibration_scores,
    )


@app.get("/v1/cri/{node_id}/history", response_model=CRIHistoryResponse)
def get_cri_history(node_id: str, limit: int = 10) -> CRIHistoryResponse:
    if limit <= 0:
        limit = 10
    if limit > 100:
        limit = 100

    node = NODE_REGISTRY.get(node_id)
    if node is None:
        return CRIHistoryResponse(node_id=node_id, history=[], total_entries=0)

    history = [asdict(entry) for entry in reversed(node.history[:])]
    return CRIHistoryResponse(node_id=node_id, history=history[:limit], total_entries=len(node.history))


@app.post("/v1/cri/update")
def update_cri(event: TransactionEvent) -> Dict[str, Any]:
    if event.node_id not in NODE_REGISTRY:
        NODE_REGISTRY[event.node_id] = create_genesis_node(event.node_id)

    node = NODE_REGISTRY[event.node_id]
    old_score = node.current_score
    event_type = event_type_for(event)
    new_score, change = calculate_cri_update(
        old_score=old_score,
        event_type=event_type,
        success=event.success,
        test_score=event.test_score,
    )

    node.current_score = new_score
    node.last_active = utc_now()

    if event.skill_id and event.skill_id not in node.capabilities:
        node.capabilities.append(event.skill_id)

    if event.calibration_test and event.test_score is not None:
        node.calibration_scores[event.skill_id] = event.test_score
    else:
        node.total_transactions += 1
        if event_type == "transaction" and event.success:
            node.successful_transactions += 1
        else:
            node.failed_transactions += 1
        update_success_rate(node)

    node.history.append(
        CRIHistoryEntry(
            timestamp=utc_now(),
            old_score=round(old_score, 4),
            new_score=new_score,
            change=change,
            reason=history_reason(event, event_type),
            transaction_id=event.transaction_id,
        )
    )

    return {
        "node_id": node.node_id,
        "old_score": round(old_score, 4),
        "new_score": new_score,
        "change": change,
        "total_transactions": node.total_transactions,
        "success_rate": round(node.success_rate, 4),
    }


@app.get("/v1/node/{node_id}/badge.svg", response_class=Response)
def badge_svg(node_id: str) -> Response:
    score = NODE_REGISTRY.get(node_id).current_score if node_id in NODE_REGISTRY else GENESIS_SCORE
    if score >= 4:
        color = "#2da44e"
    elif score >= 3:
        color = "#1f6feb"
    elif score >= 2:
        color = "#d29922"
    else:
        color = "#cf222e"

    score_value = f"{score:.2f}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="180" height="20" role="img" aria-label="BotNode CRI: {score_value}">
<rect width="95" height="20" fill="#555"/>
<rect x="95" width="85" height="20" fill="{color}"/>
<text x="48" y="14" fill="#fff" font-family="Verdana,Geneva,sans-serif" font-size="11" text-anchor="middle">BotNode CRI</text>
<text x="137" y="14" fill="#fff" font-family="Verdana,Geneva,sans-serif" font-size="11" text-anchor="middle">{score_value}</text>
</svg>"""
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/v1/calibration/tests")
def list_calibration_tests(limit: int = 20) -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []
    for node in NODE_REGISTRY.values():
        for entry in reversed(node.history[:]):
            if entry.reason.startswith("Calibration test"):
                test_record = asdict(entry)
                test_record["node_id"] = node.node_id
                tests.append(test_record)
    return {"tests": tests[:max(1, min(limit, 100))], "total": len(tests)}


@app.get("/stats")
def stats() -> Dict[str, Any]:
    total_nodes = len(NODE_REGISTRY)
    if total_nodes == 0:
        return {
            "total_nodes": 0,
            "average_cri": 0.0,
            "total_transactions": 0,
            "active_today": 0,
            "nodes_by_score": {
                "excellent_4+": 0,
                "good_3-4": 0,
                "fair_2-3": 0,
                "poor_1-2": 0,
                "critical_0-1": 0,
            },
        }

    average_cri = sum(node.current_score for node in NODE_REGISTRY.values()) / total_nodes
    total_transactions = sum(node.total_transactions for node in NODE_REGISTRY.values())
    today = datetime.utcnow().date()
    active_today = sum(
        1 for node in NODE_REGISTRY.values() if datetime.fromisoformat(node.last_active.replace("Z", "")).date() == today
    )

    nodes_by_score = {
        "excellent_4+": 0,
        "good_3-4": 0,
        "fair_2-3": 0,
        "poor_1-2": 0,
        "critical_0-1": 0,
    }
    for node in NODE_REGISTRY.values():
        score = node.current_score
        if score >= 4:
            nodes_by_score["excellent_4+"] += 1
        elif score >= 3:
            nodes_by_score["good_3-4"] += 1
        elif score >= 2:
            nodes_by_score["fair_2-3"] += 1
        elif score >= 1:
            nodes_by_score["poor_1-2"] += 1
        else:
            nodes_by_score["critical_0-1"] += 1

    return {
        "total_nodes": total_nodes,
        "average_cri": round(average_cri, 2),
        "total_transactions": total_transactions,
        "active_today": active_today,
        "nodes_by_score": nodes_by_score,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8111)
