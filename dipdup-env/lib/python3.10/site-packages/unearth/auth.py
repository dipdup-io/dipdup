from __future__ import annotations

import abc
import getpass
import logging
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Literal, Optional, Tuple, cast
from urllib.parse import SplitResult, urlparse, urlsplit

from httpx import URL, Auth, BasicAuth

from unearth.utils import commonprefix, get_netrc_auth, split_auth_from_url

if TYPE_CHECKING:
    from typing import Any, Callable, Generator, Iterable

    from httpx import Request, Response
    from requests import Response as RequestsResponse
    from requests.models import PreparedRequest

KEYRING_DISABLED = False

AuthInfo = Tuple[str, str]
MaybeAuth = Optional[Tuple[str, Optional[str]]]
logger = logging.getLogger(__name__)


def _expect_argument(func: Callable[..., Any], argname: str) -> bool:
    """Return True if the function expects the argument."""
    import inspect

    sig = inspect.signature(func)
    return argname in sig.parameters


class KeyringBaseProvider(metaclass=abc.ABCMeta):
    """Base class for keyring providers."""

    @abc.abstractmethod
    def get_auth_info(self, url: str, username: str | None) -> AuthInfo | None:
        """Return the password for the given url and username.
        The username can be None.
        """
        ...

    @abc.abstractmethod
    def save_auth_info(self, url: str, username: str, password: str) -> None:
        """Set the password for the given url and username."""
        ...

    @abc.abstractmethod
    def delete_auth_info(self, url: str, username: str) -> None:
        """Delete the password for the given url and username."""
        ...


class KeyringModuleProvider(KeyringBaseProvider):
    """Keyring provider that uses the keyring module."""

    def __init__(self) -> None:
        import keyring

        self.keyring = keyring

    def get_auth_info(self, url: str, username: str | None) -> AuthInfo | None:
        if hasattr(self.keyring, "get_credential"):
            logger.debug("Getting credentials from keyring for url: %s", url)
            cred = self.keyring.get_credential(url, username)
            if cred is not None:
                return cred.username, cred.password

        if username is None:
            username = "__token__"
        logger.debug("Getting password from keyring for: %s@%s", username, url)
        password = self.keyring.get_password(url, username)
        if password:
            return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        self.keyring.set_password(url, username, password)

    def delete_auth_info(self, url: str, username: str) -> None:
        self.keyring.delete_password(url, username)


class KeyringCliProvider(KeyringBaseProvider):
    def __init__(self, cmd: str) -> None:
        self.keyring = cmd

    def get_auth_info(self, url: str, username: str | None) -> AuthInfo | None:
        logger.debug("Getting credentials from keyring CLI for url: %s", url)
        cred = self._get_secret(url, username or "", mode="creds")
        if cred is not None:
            username, password = cred.splitlines()
            return username, password

        if username is None:
            username = "__token__"
        logger.debug("Getting password from keyring CLI for %s@%s", username, url)
        password = self._get_secret(url, username)  # type: ignore[assignment]
        if password is not None:
            return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return self._set_password(url, username, password)

    def delete_auth_info(self, url: str, username: str) -> None:
        cmd = [self.keyring, "del", url, username]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        subprocess.run(cmd, env=env, check=True)

    def _get_secret(
        self,
        service_name: str,
        username: str,
        mode: Literal["password", "creds"] = "password",
    ) -> str | None:
        """Mirror the implementation of keyring.get_[password|credential] using cli"""
        cmd = [self.keyring, f"--mode={mode}", "get", service_name, username]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        res = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, capture_output=True, env=env
        )
        if res.returncode:
            return None
        return res.stdout.decode("utf-8").strip(os.linesep)

    def _set_password(self, service_name: str, username: str, password: str) -> None:
        """Mirror the implementation of keyring.set_password using cli"""
        if self.keyring is None:
            return None

        cmd = [self.keyring, "set", service_name, username]
        input_ = (password + os.linesep).encode("utf-8")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        subprocess.run(cmd, input=input_, env=env, check=True)


def get_keyring_provider() -> KeyringBaseProvider | None:
    """Return the keyring provider to use."""
    if KEYRING_DISABLED:
        return None

    try:
        return KeyringModuleProvider()
    except ImportError:
        pass
    except Exception as exc:
        logger.warning(
            "Importing keyring failed: %s, trying to find a keyring executable.",
            exc,
        )

    keyring = shutil.which("keyring")
    if keyring is not None:
        return KeyringCliProvider(keyring)

    return None


def get_keyring_auth(url: str | None, username: str | None) -> AuthInfo | None:
    """Return the tuple auth for a given url from keyring."""
    if not url:
        return None

    keyring = get_keyring_provider()
    if keyring is None:
        return None
    try:
        return keyring.get_auth_info(url, username)
    except Exception as exc:
        logger.warning(
            "Keyring is skipped due to an exception: %s",
            str(exc),
        )
        global KEYRING_DISABLED
        KEYRING_DISABLED = True
        return None


class MultiDomainBasicAuth(Auth):
    """A multi-domain HTTP basic authentication handler supporting both requests and httpx"""

    def __init__(self, prompting: bool = True, index_urls: Iterable[str] = ()) -> None:
        self.prompting = prompting
        self.index_urls = list(index_urls)

        self._cached_passwords: dict[str, AuthInfo] = {}
        self._credentials_to_save: tuple[str, str, str] | None = None

    def _get_auth_from_index_url(self, url: str) -> tuple[MaybeAuth, str | None]:
        """Return the extracted auth and the original index URL matching
        the requested url. The auth part should be already stripped from the URL.

        Returns None if no matching index was found, or if --no-index
        was specified by the user.
        """
        if not url or not self.index_urls:
            return None, None

        target = urlsplit(url.rstrip("/") + "/")
        candidates: list[SplitResult] = []

        for index in self.index_urls:
            index = index.rstrip("/") + "/"
            auth, url_no_auth = split_auth_from_url(index)
            parsed = urlsplit(url_no_auth)
            if parsed == target:
                return auth, index

            if target.netloc == parsed.netloc:
                candidates.append(urlsplit(index))

        if not candidates:
            return None, None
        best_match = max(
            candidates, key=lambda x: commonprefix(x.path, target.path).rfind("/")
        )
        index = best_match.geturl()
        return split_auth_from_url(index)[0], index

    def _get_new_credentials(
        self,
        original_url: str,
        *,
        allow_netrc: bool = True,
        allow_keyring: bool = False,
    ) -> tuple[str | None, str | None]:
        """Find and return credentials for the specified URL."""
        # Split the credentials and netloc from the url.
        auth, url = split_auth_from_url(original_url)
        netloc = urlparse(url).netloc

        # Start with the credentials embedded in the url
        username, password = None, None
        if auth:
            username, password = auth
            if password is not None:
                logger.debug("Found credentials in url for %s", netloc)
                return cast(AuthInfo, auth)

        # Find a matching index url for this request
        # XXX: a compatiblity layer to support old function signature
        if _expect_argument(self._get_auth_from_index_url, "netloc"):
            index_auth, index_url = self._get_auth_from_index_url(netloc)
        else:
            index_auth, index_url = self._get_auth_from_index_url(url)

        if index_url:
            logger.debug("Found index url %s", index_url)

            # If an index URL was found, try its embedded credentials
            if index_auth is not None:
                if index_auth[1] is not None:
                    logger.debug("Found credentials in index url for %s", netloc)
                    return cast(AuthInfo, index_auth)
                if username is None:
                    username = index_auth[0]

        # Get creds from netrc if we still don't have them
        if allow_netrc:
            netrc_auth = get_netrc_auth(original_url)
            if netrc_auth:
                logger.debug("Found credentials in netrc for %s", netloc)
                return cast(AuthInfo, netrc_auth)

        # If we don't have a password and keyring is available, use it.
        if allow_keyring:
            # The index url is more specific than the netloc, so try it first
            kr_auth = get_keyring_auth(index_url, username) or get_keyring_auth(
                netloc, username
            )
            if kr_auth:
                logger.debug("Found credentials in keyring for %s", netloc)
                return kr_auth

        return username, password

    def _get_url_and_credentials(
        self, original_url: str
    ) -> tuple[str, str | None, str | None]:
        """Return the credentials to use for the provided URL.

        If allowed, netrc and keyring may be used to obtain the
        correct credentials.

        Returns (url_without_credentials, username, password). Note
        that even if the original URL contains credentials, this
        function may return a different username and password.
        """
        _, url = split_auth_from_url(original_url)
        netloc = urlparse(url).netloc
        # Try to get credentials from original url
        username, password = self._get_new_credentials(
            original_url, allow_netrc=True, allow_keyring=False
        )

        # If credentials not found, use any stored credentials for this netloc.
        # Do this if either the username or the password is missing.
        # This accounts for the situation in which the user has specified
        # the username in the index url, but the password comes from keyring.
        if (username is None or password is None) and netloc in self._cached_passwords:
            un, pw = self._cached_passwords[netloc]
            # It is possible that the cached credentials are for a different username,
            # in which case the cache should be ignored.
            if username is None or username == un:
                username, password = un, pw

        if username is not None or password is not None:
            # Store any acquired credentials.
            self._cached_passwords[netloc] = (username or "", password or "")

        return url, username, password

    def __call__(self, req: PreparedRequest) -> PreparedRequest:
        # Get credentials for this request
        from requests.auth import HTTPBasicAuth

        url, username, password = self._get_url_and_credentials(cast(str, req.url))
        req.url = url

        if username is not None and password is not None:
            req = HTTPBasicAuth(username, password)(req)

        # Attach a hook to handle 401 responses
        req.register_hook("response", self.handle_401)

        return req

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        url, username, password = self._get_url_and_credentials(str(request.url))
        request.url = URL(url)

        if username is not None and password is not None:
            basic_auth = BasicAuth(username, password)
            request = next(basic_auth.auth_flow(request))

        response = yield request

        if response.status_code != 401:
            return

        # Query the keyring for credentials:
        username, password = self._get_new_credentials(
            url, allow_netrc=False, allow_keyring=True
        )

        # Prompt the user for a new username and password
        save = False
        netloc = response.url.netloc.decode()
        if password is None:
            # We are not able to prompt the user so simply return the response
            if not self.prompting:
                return

            if _expect_argument(self._prompt_for_password, "username"):
                username, password, save = self._prompt_for_password(netloc, username)
            else:
                username, password, save = self._prompt_for_password(netloc)

        # Store the new username and password to use for future requests
        self._credentials_to_save = None
        if username is not None and password is not None:
            self._cached_passwords[netloc] = (username, password)

            # Prompt to save the password to keyring
            if save and self._should_save_password_to_keyring():
                self._credentials_to_save = (netloc, username, password)

        # Add our new username and password to the request
        basic_auth = BasicAuth(username or "", password or "")
        request = next(basic_auth.auth_flow(request))

        response = yield request
        self.warn_on_401(response)

        # On successful request, save the credentials that were used to
        # keyring. (Note that if the user responded "no" above, this member
        # is not set and nothing will be saved.)
        if self._credentials_to_save:
            self.save_credentials(response)

    # Factored out to allow for easy patching in tests
    def _prompt_for_password(
        self, netloc: str, username: str | None = None
    ) -> tuple[str | None, str | None, bool]:
        if username is None:
            username = input(f"User for {netloc}: ")
            auth = get_keyring_auth(netloc, username)
            if auth and auth[0] is not None and auth[1] is not None:
                return (*auth, False)
        else:
            logger.info("Username: %s", username)
        if not username:
            return None, None, False
        password = getpass.getpass("Password: ")
        return username, password, True

    # Factored out to allow for easy patching in tests
    def _should_save_password_to_keyring(self) -> bool:
        if get_keyring_provider() is None:
            return False
        return input("Save credentials to keyring [y/N]: ") == "y"

    def handle_401(self, resp: RequestsResponse, **kwargs: Any) -> Response:
        # We only care about 401 response, anything else we want to just
        #   pass through the actual response
        from requests.auth import HTTPBasicAuth

        if resp.status_code != 401:
            return resp

        parsed = urlparse(cast(str, resp.url))

        # Query the keyring for credentials:
        username, password = self._get_new_credentials(
            resp.url,
            allow_netrc=False,
            allow_keyring=True,
        )

        # Prompt the user for a new username and password
        save = False
        if password is None:
            # We are not able to prompt the user so simply return the response
            if not self.prompting:
                return resp

            if _expect_argument(self._prompt_for_password, "username"):
                username, password, save = self._prompt_for_password(
                    parsed.netloc, username
                )
            else:
                username, password, save = self._prompt_for_password(parsed.netloc)

        # Store the new username and password to use for future requests
        self._credentials_to_save = None
        if username is not None and password is not None:
            self._cached_passwords[parsed.netloc] = (username, password)

            # Prompt to save the password to keyring
            if save and self._should_save_password_to_keyring():
                self._credentials_to_save = (parsed.netloc, username, password)

        # Consume content and release the original connection to allow our new
        #   request to reuse the same one.
        resp.content
        resp.raw.release_conn()

        # Add our new username and password to the request
        req = HTTPBasicAuth(username or "", password or "")(resp.request)
        # We add new hooks on the fly, since the req is the same as resp.request
        # The hook will be picked up by the next iteration of `dispatch_hooks()`
        req.register_hook("response", self.warn_on_401)

        # On successful request, save the credentials that were used to
        # keyring. (Note that if the user responded "no" above, this member
        # is not set and nothing will be saved.)
        if self._credentials_to_save:
            req.register_hook("response", self.save_credentials)

        # Send our new request
        new_resp = resp.connection.send(req, **kwargs)  # type: ignore[attr-defined]
        new_resp.history.append(resp)

        return new_resp

    def warn_on_401(self, resp: Response | RequestsResponse, **kwargs: Any) -> None:
        """Response callback to warn about incorrect credentials."""
        if resp.status_code == 401:
            logger.warning(
                "%s Error, Credentials not correct for %s",
                resp.status_code,
                resp.request.url,
            )

    def save_credentials(
        self, resp: Response | RequestsResponse, **kwargs: Any
    ) -> None:
        """Response callback to save credentials on success."""
        keyring = get_keyring_provider()
        assert keyring is not None, "should never reach here without keyring"

        creds = self._credentials_to_save
        self._credentials_to_save = None
        if creds and resp.status_code < 400:
            try:
                logger.info("Saving credentials to keyring")
                keyring.save_auth_info(*creds)
            except Exception:
                logger.exception("Failed to save credentials")
