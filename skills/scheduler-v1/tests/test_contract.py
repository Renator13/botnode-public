import asyncio

from scheduler_v1.engine import SchedulerEngine
from scheduler_v1.models import SchedulerInput


def test_scheduler_returns_next_run(tmp_path) -> None:
    engine = SchedulerEngine(db_path=str(tmp_path / "scheduler.db"))
    payload = SchedulerInput(
        cron_expression="0 8 * * *",
        target_node_id="node-self",
        task_payload={"action": "run_report"},
        timezone="UTC",
    )

    output = asyncio.run(engine.run(payload))
    assert output.status == "scheduled"
    assert output.job_id.startswith("job-")
    assert output.next_run.endswith("Z")
