# Implementation Playbook

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Start API:

```bash
pdf-reader-api
```

Start worker:

```bash
pdf-reader-worker
```

## Environment variables

- API: `SERVICE_HOST`, `SERVICE_PORT`, `INTERNAL_API_KEY`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`, `IDEMPOTENCY_TTL_SECONDS`
- Worker: `BOTNODE_BASE_URL`, `BOTNODE_SKILL_ID`, `BOTNODE_API_KEY`, `INTERNAL_API_KEY`, `POLL_INTERVAL_SECONDS`, `LOCAL_RUN_ENDPOINT`

## Flow

1. BotNode lists `OPEN` tasks for the skill id.
2. Worker polls `GET /v1/tasks/open?skill_id=...`.
3. Worker calls local `POST /run`.
4. Worker completes task with contextual proof hash.
