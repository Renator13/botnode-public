import pytest
from pydantic import ValidationError

from code_reviewer_v1.models import CodeReviewInput


def test_input_model_has_no_url_surface() -> None:
    with pytest.raises(ValidationError):
        CodeReviewInput(
            language="python",
            code="print('x')",
            context="test",
            url="http://127.0.0.1/",  # type: ignore[call-arg]
        )
