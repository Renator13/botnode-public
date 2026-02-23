from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from .models import BotNodeTask, LeadEnricherOutput


logger = logging.getLogger("lead_enricher_v1.worker")


def _required_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
LOCAL_RUN_ENDPOINT = os.getenv("LOCAL_RUN_ENDPOINT", "http://127.0.0.1:8080/run")


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def worker_loop() -> None:
    base_url = _required_env("BOTNODE_BASE_URL").rstrip("/")
    skill_id = _required_env("BOTNODE_SKILL_ID")
    api_key = _required_env("BOTNODE_API_KEY")
    internal_api_key = _required_env("INTERNAL_API_KEY")

    timeout = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            try:
                tasks = await _fetch_open_tasks(client, base_url, skill_id, api_key)
                for task in tasks:
                    await _process_task(client, base_url, skill_id, api_key, internal_api_key, task)
            except Exception as exc:
                logger.exception("worker loop failed: %s", exc)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _fetch_open_tasks(
    client: httpx.AsyncClient,
    base_url: str,
    skill_id: str,
    api_key: str,
) -> List[BotNodeTask]:
    response = await _request_with_retries(
        client=client,
        method="GET",
        url=f"{base_url}/v1/tasks/open",
        headers=_headers(api_key),
        params={"skill_id": skill_id},
    )

    if response.status_code != 200:
        raise RuntimeError(f"open tasks failed: status={response.status_code} body={response.text[:500]}")

    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("open tasks response must be a JSON list")

    tasks: List[BotNodeTask] = []
    for item in payload:
        try:
            tasks.append(BotNodeTask.model_validate(item))
        except Exception as exc:
            logger.warning("skipping malformed task payload: %s", exc)

    return tasks


async def _process_task(
    client: httpx.AsyncClient,
    base_url: str,
    skill_id: str,
    api_key: str,
    internal_api_key: str,
    task: BotNodeTask,
) -> None:
    task_id = str(task.id)
    logger.info("processing task_id=%s", task_id)

    output_data = await _run_local_service(
        client=client,
        input_data=task.input_data,
        task_id=task_id,
        skill_id=skill_id,
        internal_api_key=internal_api_key,
    )

    proof_hash = _compute_contextual_proof_hash(
        task_id=task_id,
        skill_id=skill_id,
        input_data=task.input_data,
        output_data=output_data,
    )

    response = await _request_with_retries(
        client=client,
        method="POST",
        url=f"{base_url}/v1/tasks/complete",
        headers=_headers(api_key),
        json_payload={
            "task_id": task_id,
            "output_data": output_data,
            "proof_hash": f"sha256:{proof_hash}",
        },
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"complete task failed: task_id={task_id} status={response.status_code} body={response.text[:500]}"
        )

    logger.info("completed task_id=%s", task_id)


async def _run_local_service(
    client: httpx.AsyncClient,
    input_data: Dict[str, Any],
    task_id: str,
    skill_id: str,
    internal_api_key: str,
) -> Dict[str, Any]:
    idempotency_key = _build_idempotency_key(task_id=task_id, skill_id=skill_id, input_data=input_data)

    response = await _request_with_retries(
        client=client,
        method="POST",
        url=LOCAL_RUN_ENDPOINT,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-INTERNAL-API-KEY": internal_api_key,
            "Idempotency-Key": idempotency_key,
        },
        json_payload=input_data,
    )

    if response.status_code != 200:
        raise RuntimeError(f"local /run failed: status={response.status_code} body={response.text[:500]}")

    output = LeadEnricherOutput.model_validate(response.json())
    return output.model_dump(mode="json")


def _build_idempotency_key(task_id: str, skill_id: str, input_data: Dict[str, Any]) -> str:
    envelope = {
        "task_id": task_id,
        "skill_id": skill_id,
        "input_data": input_data,
    }
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _compute_contextual_proof_hash(
    task_id: str,
    skill_id: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
) -> str:
    envelope = {
        "task_id": task_id,
        "skill_id": skill_id,
        "input_data": input_data,
        "output_data": output_data,
    }
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def _request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    json_payload: Optional[Dict[str, Any]] = None,
    max_attempts: int = 4,
) -> httpx.Response:
    last_exc: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            response = await client.request(method=method, url=url, headers=headers, params=params, json=json_payload)
            if response.status_code >= 500 and attempt < max_attempts - 1:
                await asyncio.sleep(0.35 * (2**attempt))
                continue
            return response
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(0.35 * (2**attempt))

    raise RuntimeError(f"request failed after retries: {method} {url}") from last_exc


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    _required_env("BOTNODE_BASE_URL")
    _required_env("BOTNODE_SKILL_ID")
    _required_env("BOTNODE_API_KEY")
    _required_env("INTERNAL_API_KEY")
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
