from __future__ import annotations

import email
import mimetypes
import os
from typing import TYPE_CHECKING

import httpx
from httpx._config import DEFAULT_LIMITS
from httpx._content import IteratorByteStream

from unearth.link import Link
from unearth.utils import parse_netloc

if TYPE_CHECKING:
    from typing import Any, ContextManager, Iterable, Mapping

    from httpx._types import CertTypes, TimeoutTypes, VerifyTypes


def is_absolute_url(self) -> bool:
    return self._uri_reference.scheme or self._uri_reference.host


# Patch the is_absolute_url method of httpx.URL to allow file:// URLs
httpx.URL.is_absolute_url = property(is_absolute_url)


class FileByteStream(IteratorByteStream):
    def close(self) -> None:
        self._stream.close()  # type: ignore[attr-defined]


class LocalFSTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        link = Link(str(request.url))
        path = link.file_path
        if request.method != "GET":
            return httpx.Response(status_code=405)

        try:
            stats = os.stat(path)
        except OSError as exc:
            # format the exception raised as a io.BytesIO object,
            # to return a better error message:
            return httpx.Response(status_code=404, text=f"{type(exc).__name__}: {exc}")
        else:
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            content_type = mimetypes.guess_type(path)[0] or "text/plain"
            headers = {
                "Content-Type": content_type,
                "Content-Length": str(stats.st_size),
                "Last-Modified": modified,
            }
            return httpx.Response(
                status_code=200,
                headers=headers,
                stream=FileByteStream(path.open("rb")),
            )


class PyPIClient(httpx.Client):
    """
    A :class:`httpx.Client` subclass that supports file:// URLs and trusted hosts configuration.

    Args:
        trusted_hosts: A list of trusted hosts. If a host is trusted, the client will not verify the SSL certificate.
        \\**kwargs: Additional keyword arguments to pass to the :class:`httpx.Client` constructor.
    """

    def __init__(
        self,
        *,
        trusted_hosts: Iterable[str] = (),
        verify: VerifyTypes = True,
        cert: CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        limits: httpx.Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        timeout: TimeoutTypes = 10.0,
        **kwargs: Any,
    ) -> None:
        self._trusted_host_ports: set[tuple[str, int | None]] = set()
        # Due to lack of ability of retry behavior in httpx, we don't support it for simplicity
        insecure_transport = httpx.HTTPTransport(
            verify=False,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits,
            trust_env=trust_env,
        )

        mounts: dict[str, httpx.BaseTransport] = {"file://": LocalFSTransport()}
        for host in trusted_hosts:
            hostname, port = parse_netloc(host)
            self._trusted_host_ports.add((hostname, port))
            mounts[f"all://{host}"] = insecure_transport

        mounts.update(kwargs.pop("mounts", {}))

        super().__init__(
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits,
            trust_env=trust_env,
            timeout=timeout,
            mounts=mounts,
            **kwargs,
        )

    def get_stream(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> ContextManager[httpx.Response]:
        return self.stream("GET", url, headers=headers)

    def iter_secure_origins(self) -> Iterable[tuple[str, str, str]]:
        from unearth.fetchers import DEFAULT_SECURE_ORIGINS

        yield from DEFAULT_SECURE_ORIGINS
        for host, port in self._trusted_host_ports:
            yield ("*", host, "*" if port is None else str(port))
