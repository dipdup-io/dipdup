from __future__ import annotations

from typing import ContextManager, Iterable, Iterator, Mapping, Protocol

from unearth.fetchers.sync import PyPIClient as PyPIClient

DEFAULT_MAX_RETRIES = 5
DEFAULT_SECURE_ORIGINS = [
    ("https", "*", "*"),
    ("wss", "*", "*"),
    ("*", "localhost", "*"),
    ("*", "127.0.0.0/8", "*"),
    ("*", "::1/128", "*"),
    ("file", "*", "*"),
]


class Response(Protocol):
    status_code: int
    headers: Mapping[str, str]
    encoding: str | None
    url: str | None

    @property
    def content(self) -> bytes: ...

    def json(self) -> dict: ...

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]: ...

    @property
    def reason_phrase(self) -> str: ...

    def raise_for_status(self) -> None: ...


class Fetcher(Protocol):
    def get(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> Response: ...

    def head(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> Response: ...

    def get_stream(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> ContextManager[Response]: ...

    def __hash__(self) -> int: ...

    def iter_secure_origins(self) -> Iterable[tuple[str, str, str]]: ...
