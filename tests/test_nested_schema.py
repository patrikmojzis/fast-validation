from __future__ import annotations

import pytest

from fast_validation import Schema, ValidatorRule, ValidationRuleException


class RecordingValidator(ValidatorRule):
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def validate(self, *, value, data, loc):
        self.calls.append(tuple(loc))


class RequireValueValidator(ValidatorRule):
    async def validate(self, *, value, data, loc):
        if value is None:
            raise ValidationRuleException(
                "value is required",
                loc=tuple(loc),
                error_type="value_error.missing",
            )


class StockPatchSchema(Schema):
    name: str | None = None
    rep_id: int | None = None

    class Meta:
        rules = [
            Schema.Rule("$.rep_id", [RequireValueValidator()]),
        ]


class UpdateStockToolSchema(Schema):
    stock_id: int
    data: StockPatchSchema

    class Meta:
        rules = [
            Schema.Rule("$.stock_id", [RequireValueValidator()]),
        ]


@pytest.mark.asyncio
async def test_nested_schema_rules_are_invoked_from_parent_validation():
    rep_rule = RecordingValidator()
    stock_rule = RecordingValidator()

    class NestedStockPatchSchema(StockPatchSchema):
        class Meta:
            rules = [
                Schema.Rule("$.rep_id", [rep_rule]),
            ]

    class NestedUpdateStockToolSchema(UpdateStockToolSchema):
        data: NestedStockPatchSchema

        class Meta:
            rules = [
                Schema.Rule("$.stock_id", [stock_rule]),
            ]

    schema = NestedUpdateStockToolSchema(stock_id=1, data={"rep_id": 2})
    await schema.validate()

    assert stock_rule.calls == [("stock_id",)]
    assert rep_rule.calls == [("rep_id",)]


@pytest.mark.asyncio
async def test_nested_schema_validation_errors_are_prefixed_with_parent_path():
    schema = UpdateStockToolSchema(stock_id=1, data={"rep_id": None})

    with pytest.raises(ValidationRuleException) as excinfo:
        await schema.validate()

    errors = excinfo.value.errors or []
    assert errors and errors[0]["loc"] == ("data", "rep_id")
