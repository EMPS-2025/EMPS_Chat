import secrets
from contextlib import contextmanager
from typing import Iterator

from starlette.requests import Request


def generate_correlation_id() -> str:
    return secrets.token_hex(8)


@contextmanager
def correlation_context(request: Request) -> Iterator[str]:
    header = request.headers.get("x-correlation-id")
    correlation_id = header or generate_correlation_id()
    try:
        yield correlation_id
    finally:
        pass


__all__ = ["generate_correlation_id", "correlation_context"]
