from __future__ import annotations

from typing import Any, List, Tuple

from pydantic import BaseModel, ConfigDict, PrivateAttr

from .exceptions import ValidationNotRunException, ValidationRuleException
from .paths import resolve_path_expressions
from .validation_rule import ValidatorRule


class Schema(BaseModel):
    """
    Base schema with optional post-parse rule validation.
    """

    _validated: dict[str, Any] | None = PrivateAttr(default=None)

    class Rule:  # Simple container for rule path and its validators
        def __init__(self, path: str, validators: List[ValidatorRule]) -> None:
            self.path = path
            self.validators = validators

    class Meta:  # Override in subclasses
        rules: List["Schema.Rule"] = []

    model_config = ConfigDict(
        str_strip_whitespace = True,
        validate_assignment = True,  # whether to validate when data changed
        from_attributes = True,  # whether to build models and look up discriminators of tagged unions using python object attributes
        use_enum_values = True,  # whether to populate models with the value property of enums, rather than the raw enum
        extra = "ignore",  # ignore extra fields
        arbitrary_types_allowed = True,  # whether arbitrary types are allowed in models
    )

    async def validate(self, *, partial: bool = False) -> None:
        self._validated = None
        nested_errors = await self._gather_nested_schema_errors(partial=partial)
        data = self.model_dump(exclude_unset=partial)

        rules: List[Schema.Rule] = getattr(self.Meta, "rules", []) or []
        errors: List[dict[str, Any]] = list(nested_errors)

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

        self._validated = data

    @property
    def validated(self) -> dict[str, Any]:
        if self._validated is None:
            raise ValidationNotRunException(
                "validated is only available after validate() succeeds"
            )
        return self._validated

    async def _gather_nested_schema_errors(self, *, partial: bool) -> List[dict[str, Any]]:
        errors: List[dict[str, Any]] = []
        fields = getattr(self.__class__, "model_fields", {}) or {}
        for field_name in fields:
            if partial and field_name not in self.model_fields_set:
                continue
            value = getattr(self, field_name, None)
            errors.extend(
                await self._collect_errors_from_value(
                    value=value,
                    loc_prefix=(field_name,),
                    partial=partial,
                )
            )
        return errors

    async def _collect_errors_from_value(
        self,
        *,
        value: Any,
        loc_prefix: Tuple[str, ...],
        partial: bool,
    ) -> List[dict[str, Any]]:
        if value is None:
            return []

        if isinstance(value, Schema):
            try:
                await value.validate(partial=partial)
            except ValidationRuleException as exc:
                return self._format_nested_errors(exc, loc_prefix)
            return []

        if isinstance(value, dict):
            errors: List[dict[str, Any]] = []
            for key, item in value.items():
                errors.extend(
                    await self._collect_errors_from_value(
                        value=item,
                        loc_prefix=loc_prefix + (str(key),),
                        partial=partial,
                    )
                )
            return errors

        if isinstance(value, (list, tuple)):
            errors: List[dict[str, Any]] = []
            for idx, item in enumerate(value):
                errors.extend(
                    await self._collect_errors_from_value(
                        value=item,
                        loc_prefix=loc_prefix + (str(idx),),
                        partial=partial,
                    )
                )
            return errors

        return []

    def _format_nested_errors(
        self,
        exc: ValidationRuleException,
        loc_prefix: Tuple[str, ...],
    ) -> List[dict[str, Any]]:
        if exc.errors:
            formatted: List[dict[str, Any]] = []
            for error in exc.errors:
                child_error = dict(error)
                raw_loc = child_error.get("loc", tuple())
                child_loc = (
                    tuple(raw_loc)
                    if isinstance(raw_loc, (list, tuple))
                    else (str(raw_loc),)
                )
                child_error["loc"] = loc_prefix + child_loc
                formatted.append(child_error)
            return formatted

        return [
            {
                "loc": loc_prefix + exc.loc,
                "msg": exc.message,
                "type": exc.error_type,
            }
        ]
