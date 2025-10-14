from __future__ import annotations

from typing import Iterable, Tuple


class ValidationError(Exception):
    def __init__(self, message: str, row: Tuple | None = None) -> None:
        self.row = row
        super().__init__(message)


def ensure_hour_range(hour: int) -> None:
    if not 0 <= hour <= 23:
        raise ValidationError(f"Hour {hour} out of range")


def ensure_quarter_range(quarter_index: int) -> None:
    if not 0 <= quarter_index <= 95:
        raise ValidationError(f"Quarter index {quarter_index} out of range")


def ensure_numeric(value: float, *, min_value: float | None = None, max_value: float | None = None) -> None:
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value {value} below minimum {min_value}")
    if max_value is not None and value > max_value:
        raise ValidationError(f"Value {value} above maximum {max_value}")


def validate_all(items: Iterable[Tuple[str, bool]]) -> None:
    for message, ok in items:
        if not ok:
            raise ValidationError(message)


__all__ = [
    "ValidationError",
    "ensure_hour_range",
    "ensure_quarter_range",
    "ensure_numeric",
    "validate_all",
]
