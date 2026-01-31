from __future__ import annotations

from typing import Any


class ValidationRuleException(ValueError):
    """
    Distinct validation error raised by schema ValidatorRules.

    Separate from Pydantic's ValidationError to distinguish post-parse rule failures.
    """

    def __init__(
        self,
        message: str,
        *,
        loc: tuple[str, ...] | None = None,
        error_type: str = "value_error",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.loc: tuple[str, ...] = loc or tuple()
        self.error_type: str = error_type
        self.errors: list[dict[str, Any]] | None = errors


class ValidationNotRunException(AttributeError):
    """
    Raised when accessing validation-only data before validate() succeeds.
    """

