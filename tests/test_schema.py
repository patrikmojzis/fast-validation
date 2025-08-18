from __future__ import annotations

import pytest

from fast_validation import (
    Schema,
    ValidatorRule,
    ValidationRuleException,
)

from fast_validation.paths import resolve_path_expressions


class MustEqual(ValidatorRule):
    def __init__(self, expected: int) -> None:
        self.expected = expected

    async def validate(self, *, value, data, loc):
        if value != self.expected:
            raise ValidationRuleException(
                f"must equal {self.expected}",
                loc=tuple(loc),
                error_type="value_error.mismatch",
            )


class ItemSchema(Schema):
    value: int

    class Meta:
        rules = [Schema.Rule("$.value", [MustEqual(42)])]


@pytest.mark.asyncio
async def test_rule_validation_failure_collects_errors():
    item = ItemSchema(value=41)
    with pytest.raises(ValidationRuleException) as excinfo:
        await item.validate()
    exc = excinfo.value
    assert isinstance(exc, ValidationRuleException)
    assert exc.error_type == "rule_error"
    assert exc.errors and exc.errors[0]["loc"] == ("value",)


def test_path_resolution_for_list_items():
    data = {"items": [{"x": 1}, {"x": 2}]}
    matches = resolve_path_expressions(data, "$.items[*].x")
    assert [(loc, v) for loc, v in matches] == [
        (("items", "0", "x"), 1),
        (("items", "1", "x"), 2),
    ]


