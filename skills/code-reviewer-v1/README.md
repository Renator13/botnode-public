# code_reviewer_v1

Python 3.9 project for the BotNode skill `code_reviewer_v1` (capability `code-reviewer`).

## Components

1. FastAPI service:
   - `GET /healthz`
   - `POST /run`
2. BotNode worker:
   - `GET /v1/tasks/open?skill_id=...`
   - `POST /v1/tasks/complete`

## Current Implementation

- Deterministic baseline review:
  - detects `eval(` / `exec(` usage as a high-severity security issue.
  - detects `TODO` as a low-severity maintainability issue.
- Prepared for LLM/linter integration (Ruff/ESLint/etc.) in a later version.

## Applied Hardening

- Per-phase timeout in the worker (`connect/read/write/pool`).
- Exponential backoff in HTTP retries.
- Contextual `proof_hash` (`task_id + skill_id + input_data + output_data`).
- SSRF surface is not applicable in this version (no URL fetching from input).

## Installation

```bash
cd /Users/renedechampsotamendi/Documents/code-reviewer-v1
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Local Execution

API:
```bash
code-reviewer-api
```

Worker:
```bash
export BOTNODE_BASE_URL="https://<YOUR_BOTNODE>"
export BOTNODE_SKILL_ID="<CODE_REVIEWER_SKILL_ID>"
export BOTNODE_API_KEY="bn_<node_id>_<secret>"
export LOCAL_RUN_ENDPOINT="http://127.0.0.1:8080/run"
code-reviewer-worker
```

## Docker Compose

```bash
cd /Users/renedechampsotamendi/Documents/code-reviewer-v1
docker compose up --build
```

Services:
- `code-reviewer-api`
- `code-reviewer-worker`
