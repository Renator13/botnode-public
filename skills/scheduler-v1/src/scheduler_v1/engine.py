from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from .models import SchedulerInput, SchedulerOutput


class SchedulerEngine:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.getenv("SCHEDULER_DB_PATH", "/tmp/scheduler_v1.db")
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._lock = asyncio.Lock()
        self._ensure_schema()

    async def run(self, payload: SchedulerInput) -> SchedulerOutput:
        fields = _parse_cron_expression(payload.cron_expression)
        next_run_utc = _compute_next_run(fields, payload.timezone)

        job_id = f"job-{uuid4().hex[:12]}"

        async with self._lock:
            await asyncio.to_thread(
                self._store_job,
                job_id,
                payload.cron_expression,
                payload.target_node_id,
                payload.timezone,
                payload.task_payload,
                next_run_utc,
            )

        return SchedulerOutput(
            job_id=job_id,
            status="scheduled",
            next_run=next_run_utc.isoformat().replace("+00:00", "Z"),
        )

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                job_id TEXT PRIMARY KEY,
                cron_expression TEXT NOT NULL,
                target_node_id TEXT NOT NULL,
                timezone TEXT NOT NULL,
                task_payload_json TEXT NOT NULL,
                next_run_utc TEXT NOT NULL,
                created_at_utc TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _store_job(
        self,
        job_id: str,
        cron_expression: str,
        target_node_id: str,
        timezone_name: str,
        task_payload: dict,
        next_run_utc: datetime,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO scheduled_jobs(
                job_id,
                cron_expression,
                target_node_id,
                timezone,
                task_payload_json,
                next_run_utc,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                cron_expression,
                target_node_id,
                timezone_name,
                json.dumps(task_payload, separators=(",", ":"), ensure_ascii=False),
                next_run_utc.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()


def _parse_cron_expression(expr: str) -> list[set[int]]:
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError("cron_expression must have 5 fields: minute hour day month weekday")

    minute = _parse_field(parts[0], 0, 59)
    hour = _parse_field(parts[1], 0, 23)
    day = _parse_field(parts[2], 1, 31)
    month = _parse_field(parts[3], 1, 12)
    weekday = _parse_field(parts[4], 0, 6)

    return [minute, hour, day, month, weekday]


def _parse_field(raw: str, minimum: int, maximum: int) -> set[int]:
    raw = raw.strip()
    if raw == "*":
        return set(range(minimum, maximum + 1))

    values: set[int] = set()
    for chunk in raw.split(","):
        piece = chunk.strip()
        if not piece:
            continue

        if piece.startswith("*/"):
            step = int(piece[2:])
            if step <= 0:
                raise ValueError("invalid cron step")
            values.update(range(minimum, maximum + 1, step))
            continue

        if "-" in piece:
            left, right = piece.split("-", 1)
            start = int(left)
            end = int(right)
            if start > end:
                raise ValueError("invalid cron range")
            if start < minimum or end > maximum:
                raise ValueError("cron value out of bounds")
            values.update(range(start, end + 1))
            continue

        value = int(piece)
        if value < minimum or value > maximum:
            raise ValueError("cron value out of bounds")
        values.add(value)

    if not values:
        raise ValueError("cron field has no values")

    return values


def _compute_next_run(fields: list[set[int]], timezone_name: str) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except Exception as exc:
        raise ValueError(f"invalid timezone: {timezone_name}") from exc
    minute_set, hour_set, day_set, month_set, weekday_set = fields

    current_local = datetime.now(tz=tz).replace(second=0, microsecond=0) + timedelta(minutes=1)

    for _ in range(60 * 24 * 370):
        weekday = (current_local.weekday() + 1) % 7
        if (
            current_local.minute in minute_set
            and current_local.hour in hour_set
            and current_local.day in day_set
            and current_local.month in month_set
            and weekday in weekday_set
        ):
            return current_local.astimezone(timezone.utc)
        current_local += timedelta(minutes=1)

    raise ValueError("could not compute next run for provided cron_expression")
