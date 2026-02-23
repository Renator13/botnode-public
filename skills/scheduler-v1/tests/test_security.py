from pydantic import ValidationError

from scheduler_v1.models import SchedulerInput


def test_model_has_no_external_url_surface() -> None:
    try:
        SchedulerInput(
            cron_expression="0 8 * * *",
            target_node_id="node-self",
            task_payload={"action": "run"},
            file_url="https://example.com",  # type: ignore[call-arg]
        )
        assert False, "expected ValidationError"
    except ValidationError:
        assert True
