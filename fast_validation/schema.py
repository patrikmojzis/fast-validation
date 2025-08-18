from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel

from .validation_rule import ValidatorRule
from .exceptions import ValidationRuleException
from .paths import resolve_path_expressions


class Schema(BaseModel):
    """
    Base schema with optional post-parse rule validation.
    """

    class Rule:  # Simple container for rule path and its validators
        def __init__(self, path: str, validators: List[ValidatorRule]) -> None:
            self.path = path
            self.validators = validators

    class Meta:  # Override in subclasses
        rules: List["Schema.Rule"] = []

    async def validate(self, *, partial: bool = False) -> None:
        data = self.model_dump(exclude_unset=partial)

        rules: List[Schema.Rule] = getattr(self.Meta, "rules", []) or []
        if not rules:
            return

        errors: List[dict[str, Any]] = []
        for rule in rules:
            matches = resolve_path_expressions(data, rule.path)
            for loc, value in matches:
                for validator in rule.validators:
                    try:
                        await validator.validate(value=value, data=data, loc=loc)
                    except ValidationRuleException as exc:
                        if exc.errors:
                            errors.extend(exc.errors)
                        else:
                            errors.append(
                                {
                                    "loc": tuple(loc) if loc else tuple(),
                                    "msg": exc.message,
                                    "type": exc.error_type,
                                }
                            )

        if errors:
            raise ValidationRuleException(
                "schema rule validation failed",
                loc=tuple(),
                error_type="rule_error",
                errors=errors,
            )


