import pytest
from pydantic import ValidationError

from code_reviewer_v1.models import CodeReviewInput


def test_code_length_limit_enforced() -> None:
    with pytest.raises(ValidationError):
        CodeReviewInput(language="python", code="x" * 20001)
