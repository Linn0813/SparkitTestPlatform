"""Tests for lightweight requirement select options."""

from app.models.requirement import RequirementStatus
from app.schemas.requirement import RequirementSelectOptionOut


def test_requirement_select_option_out_from_dict():
    out = RequirementSelectOptionOut(
        id="req-1",
        num=42,
        title="登录优化",
        status=RequirementStatus.draft,
    )
    assert out.num == 42
    assert out.title == "登录优化"
