"""Collect links from simple index or find links location."""

from __future__ import annotations

import ipaddress
import json
import logging
import mimetypes
from datetime import datetime
from html.parser import HTMLParser
from typing import Iterable, Mapping, NamedTuple
from urllib import parse

from unearth.fetchers import Fetcher, Response
from unearth.link import Link
from unearth.utils import is_archive_file, path_to_url

SUPPORTED_CONTENT_TYPES = (
    "text/html",
    "application/vnd.pypi.simple.v1+html",
    "application/vnd.pypi.simple.v1+json",
)
logger = logging.getLogger(__name__)


class LinkCollectError(Exception):
    pass


class IndexPage(NamedTuple):
    link: Link
    content: bytes
    encoding: str | None
    content_type: str


class IndexHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.base_url: str | None = None
        self.anchors: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "base" and self.base_url is None:
            base_url = dict(attrs).get("href")
            if base_url is not None:
                self.base_url = base_url
        elif tag == "a":
            self.anchors.append(dict(attrs))


def _compare_origin_part(allowed: str, actual: str) -> bool:
    return allowed == "*" or allowed == actual


def is_secure_origin(fetcher: Fetcher, location: Link) -> bool:
    """
    Determine if the origin is a trusted host.

    Args:
        location (Link): The location to check.
    """
    _, _, scheme = location.parsed.scheme.rpartition("+")
    host, port = location.parsed.hostname or "", location.parsed.port
    for secure_scheme, secure_host, secure_port in fetcher.iter_secure_origins():
        if not _compare_origin_part(secure_scheme, scheme):
            continue
        try:
            addr = ipaddress.ip_address(host)
            network = ipaddress.ip_network(secure_host)
        except ValueError:
            # Either addr or network is invalid
            if not _compare_origin_part(secure_host, host):
                continue
        else:
            if addr not in network:
                continue

        if not _compare_origin_part(secure_port, "*" if port is None else str(port)):
            continue
        # We've got here, so all the parts match
        return True

    logger.warning(
        "Skipping %s for not being trusted, please add it to `trusted_hosts` list",
        location.redacted,
    )
    return False


def parse_html_page(page: IndexPage) -> Iterable[Link]:
    """PEP 503 simple index API"""
    parser = IndexHTMLParser()
    parser.feed(page.content.decode(page.encoding or "utf-8"))
    base_url = parser.base_url or page.link.url_without_fragment
    for anchor in parser.anchors:
        href = anchor.get("href")
        if href is None:
            continue
        url = parse.urljoin(base_url, href)
        requires_python = anchor.get("data-requires-python")
        yank_reason = anchor.get("data-yanked")
        metadata_hash = anchor.get(
            "data-core-metadata", anchor.get("data-dist-info-metadata")
        )
        dist_info_metadata: bool | dict[str, str] | None = None
        if metadata_hash:
            hash_name, has_hash, hash_value = metadata_hash.partition("=")
            if has_hash:
                dist_info_metadata = {hash_name: hash_value}
            else:
                dist_info_metadata = True
        yield Link(
            url,
            base_url,
            yank_reason=yank_reason,
            requires_python=requires_python,
            dist_info_metadata=dist_info_metadata,
        )


def parse_json_response(page: IndexPage) -> Iterable[Link]:
    """PEP 691 JSON simple API"""
    data = json.loads(page.content)
    base_url = page.link.url_without_fragment
    for file in data.get("files", []):
        url = file.get("url")
        if not url:
            continue
        url = parse.urljoin(base_url, url)
        requires_python: str | None = file.get("requires-python")
        yank_reason: str | None = file.get("yanked") or None
        dist_info_metadata: bool | dict[str, str] | None = file.get(
            "core-metadata", file.get("data-dist-info-metadata")
        )
        hashes: dict[str, str] | None = file.get("hashes")
        yield Link(
            url,
            base_url,
            yank_reason=yank_reason,
            requires_python=requires_python,
            dist_info_metadata=dist_info_metadata,
            hashes=hashes,
            upload_time=datetime.fromisoformat(upload_time.replace("Z", "+00:00"))
            if (upload_time := file.get("upload-time"))
            else None,
        )


def collect_links_from_location(
    session: Fetcher,
    location: Link,
    expand: bool = False,
    headers: Mapping[str, str] | None = None,
) -> Iterable[Link]:
    """Collect package links from a remote URL or local path.

    If the path is a directory and expand is True, collect links from all HTML files
    as well as local artifacts. Otherwise, collect links from $dir/index.html.
    If the path is a file, parse it and collect links from it.
    """
    logger.debug("Collecting links from %s", location.redacted)
    if location.is_file:
        path = location.file_path
        if path.is_dir():
            if expand:
                for child in path.iterdir():
                    file_url = path_to_url(str(child))
                    if _is_html_file(file_url):
                        yield from _collect_links_from_index(
                            session, Link(file_url), headers
                        )
                    else:
                        yield Link(file_url)
            else:
                index_html = Link(path_to_url(path.joinpath("index.html").as_posix()))
                yield from _collect_links_from_index(session, index_html, headers)
        else:
            if _is_html_file(str(path)):
                yield from _collect_links_from_index(session, location, headers)
            else:
                yield location

    else:  # remote url, can be either a remote file or an index URL containing files
        if is_secure_origin(session, location) and not location.is_vcs:
            yield location
        yield from _collect_links_from_index(session, location)


def fetch_page(
    session: Fetcher, location: Link, headers: Mapping[str, str] | None = None
) -> IndexPage:
    if location.is_vcs:
        raise LinkCollectError("It is a VCS link.")
    resp = _get_html_response(session, location, headers)
    from_cache = getattr(resp, "from_cache", False)
    cache_text = " (from cache)" if from_cache else ""
    logger.debug("Fetching HTML page %s%s", location.redacted, cache_text)
    return IndexPage(
        Link(str(resp.url)), resp.content, resp.encoding, resp.headers["Content-Type"]
    )


def _collect_links_from_index(
    session: Fetcher, location: Link, headers: Mapping[str, str] | None = None
) -> Iterable[Link]:
    if not is_secure_origin(session, location):
        return []
    try:
        page = fetch_page(session, location, headers)
    except LinkCollectError as e:
        logger.warning("Failed to collect links from %s: %s", location.redacted, e)
        return []
    else:
        content_type_l = page.content_type.lower()
        if content_type_l.startswith("application/vnd.pypi.simple.v1+json"):
            return parse_json_response(page)
        else:
            return parse_html_page(page)


def _is_html_file(file_url: str) -> bool:
    return mimetypes.guess_type(file_url, strict=False)[0] == "text/html"


def _get_html_response(
    session: Fetcher, location: Link, headers: Mapping[str, str] | None = None
) -> Response:
    if is_archive_file(location.filename):
        # If the URL looks like a file, send a HEAD request to ensure
        # the link is an HTML page to avoid downloading a large file.
        _ensure_index_response(session, location)

    resp = session.get(
        location.normalized,
        headers={
            "Accept": ", ".join(
                [
                    "application/vnd.pypi.simple.v1+json",
                    "application/vnd.pypi.simple.v1+html; q=0.1",
                    "text/html; q=0.01",
                ]
            ),
            **(headers or {}),
        },
    )
    _check_for_status(resp)
    _ensure_index_content_type(resp)
    return resp


def _ensure_index_response(session: Fetcher, location: Link) -> None:
    if location.parsed.scheme not in {"http", "https"}:
        raise LinkCollectError(
            "NotHTTP: the file looks like an archive but its content-type "
            "cannot be checked by a HEAD request."
        )

    resp = session.head(location.url)
    _check_for_status(resp)
    _ensure_index_content_type(resp)


def _check_for_status(resp: Response) -> None:
    if hasattr(resp, "reason"):
        reason = resp.reason
    else:
        reason = resp.reason_phrase

    if isinstance(reason, bytes):
        try:
            reason = reason.decode("utf-8")
        except UnicodeDecodeError:
            reason = reason.decode("iso-8859-1")

    if 400 <= resp.status_code < 500:
        raise LinkCollectError(f"Client Error({resp.status_code}): {reason}")
    if 500 <= resp.status_code < 600:
        raise LinkCollectError(f"Server Error({resp.status_code}): {reason}")


def _ensure_index_content_type(resp: Response) -> None:
    content_type = resp.headers.get("Content-Type", "Unknown")

    content_type_l = content_type.lower()
    if content_type_l.startswith(SUPPORTED_CONTENT_TYPES):
        return

    raise LinkCollectError(
        f"Content-Type unsupported: {content_type}. "
        f"The only supported are {', '.join(SUPPORTED_CONTENT_TYPES)}."
    )
