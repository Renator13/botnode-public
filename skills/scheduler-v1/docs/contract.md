# Contract: scheduler_v1

## Objective
Schedule tasks at specific intervals using cron expressions.

## Input
```json
{
  "cron_expression": "0 8 * * *",
  "target_node_id": "node-self",
  "task_payload": {
    "action": "run_report",
    "params": {"id": 123}
  },
  "timezone": "UTC"
}
```

## Output
```json
{
  "job_id": "job-12345",
  "status": "scheduled",
  "next_run": "2026-02-17T08:00:00Z"
}
```
