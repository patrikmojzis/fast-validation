from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence


class ValidatorRule(ABC):
    """Contract for post-parse validation rules used by `Schema`."""

    @abstractmethod
    async def validate(self, *, value: Any, data: dict, loc: Sequence[str]) -> None:  # pragma: no cover - interface only
        """
        Validate a value within the context of the entire payload.

        Raises:
            ValidationRuleException: If the validation fails.
        """
        raise NotImplementedError


