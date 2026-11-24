"""A tiny read-only GitHub API client (REST + GraphQL) built on ``urllib``.

It only sends GET requests and GraphQL *queries*; there is no code path that
writes to GitHub. It tracks the rate-limit budget from response headers, backs
off when the wait is short, and turns every failure into a :class:`GitHubError`
whose message is safe to show (the token never appears in it).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from . import __version__

API_URL = "https://api.github.com"
USER_AGENT = (
    f"github-achievements-progress/{__version__} "
    "(+https://github.com/Shahnawaz75/github-achievements-progress)"
)

#: ``transport(method, url, headers, body, timeout) -> (status, headers, body)``.
#: Tests replace it with a fake; HTTP error statuses are returned, not raised.
Transport = Callable[
    [str, str, Dict[str, str], Optional[bytes], float], Tuple[int, Mapping[str, str], bytes]
]


class GitHubError(Exception):
    """Any problem talking to GitHub. The message is meant for humans."""


class NotFoundError(GitHubError):
    """The user or resource does not exist, or this token cannot see it."""


class AuthError(GitHubError):
    """The token was rejected, or the request needs a token."""


class RateLimitError(GitHubError):
    """The rate limit is used up and the reset is too far away to wait for."""


class NetworkError(GitHubError):
    """GitHub could not be reached."""


def urllib_transport(
    method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float
) -> Tuple[int, Mapping[str, str], bytes]:
    """Send one HTTP request with urllib."""
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers.items()) if err.headers else {}, err.read()
    except (urllib.error.URLError, OSError) as err:
        reason = getattr(err, "reason", err)
        raise NetworkError(f"could not reach GitHub ({reason}); check your connection") from None


def _parse_json(raw: bytes) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {}


class GitHubClient:
    """Read-only GitHub API client. The token is stored privately and never printed."""

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        transport: Optional[Transport] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        on_wait: Optional[Callable[[str], None]] = None,
        max_wait: float = 60.0,
        retries: int = 2,
        timeout: float = 20.0,
        api_url: str = API_URL,
    ) -> None:
        self._token = token or None
        self._transport = transport or urllib_transport
        self._sleep, self._clock, self._on_wait = sleep, clock, on_wait
        self.max_wait, self.retries, self.timeout = max_wait, retries, timeout
        self.api_url = api_url.rstrip("/")
        self.rate: Dict[str, Dict[str, int]] = {}
        self.calls = 0

    def __repr__(self) -> str:
        return f"GitHubClient(authenticated={self.authenticated}, calls={self.calls})"

    @property
    def authenticated(self) -> bool:
        """True when a token is used."""
        return self._token is not None

    def rest(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        """GET a REST endpoint such as ``/users/octocat`` and return the parsed JSON."""
        url = self.api_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return self._request("GET", url, None)

    def graphql(self, query: str, variables: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Run a GraphQL query and return its ``data`` (partial data is returned as is)."""
        if not self.authenticated:
            raise AuthError("this check needs a token: GitHub's GraphQL API has no anonymous access")
        body = json.dumps({"query": query, "variables": dict(variables or {})}).encode("utf-8")
        result = self._request("POST", self.api_url + "/graphql", body) or {}
        errors = result.get("errors") or []
        if any(error.get("type") == "RATE_LIMITED" for error in errors):
            raise RateLimitError(self._limit_message("graphql"))
        if result.get("data") is None:
            message = errors[0].get("message", "unknown error") if errors else "empty response"
            raise GitHubError(f"GitHub GraphQL error: {message}")
        return result["data"]

    def rate_summary(self) -> Dict[str, Dict[str, Any]]:
        """The remaining budget per API resource, from the latest response headers."""
        return {
            name: {
                "remaining": info["remaining"],
                "limit": info["limit"],
                "reset": datetime.fromtimestamp(info["reset"], tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
            for name, info in sorted(self.rate.items())
        }

    def _request(self, method: str, url: str, body: Optional[bytes]) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        resource = "core"
        for attempt in range(self.retries + 1):
            self.calls += 1
            status, raw_headers, raw = self._transport(method, url, headers, body, self.timeout)
            lowered = {key.lower(): value for key, value in raw_headers.items()}
            resource = self._track(lowered)
            data = _parse_json(raw)
            message = str(data.get("message", "")) if isinstance(data, dict) else ""
            if status in (403, 429) and self._is_rate_limited(lowered, message):
                wait = self._wait_seconds(lowered)
                if attempt < self.retries and wait <= self.max_wait:
                    if self._on_wait:
                        self._on_wait(f"GitHub rate limit on the '{resource}' API: waiting {wait:.0f}s")
                    self._sleep(max(wait, 1.0))
                    continue
                raise RateLimitError(self._limit_message(resource))
            if status == 401:
                raise AuthError("GitHub rejected the token (401); check GITHUB_TOKEN or use --no-token")
            if status == 404:
                raise NotFoundError(f"not found: {urllib.parse.urlsplit(url).path}")
            if status >= 400:
                raise GitHubError(f"GitHub API error {status}: {message or 'no details'}")
            return data
        raise RateLimitError(self._limit_message(resource))  # pragma: no cover

    def _track(self, headers: Mapping[str, str]) -> str:
        resource = headers.get("x-ratelimit-resource", "core")
        try:
            self.rate[resource] = {
                "limit": int(headers["x-ratelimit-limit"]),
                "remaining": int(headers["x-ratelimit-remaining"]),
                "reset": int(headers["x-ratelimit-reset"]),
            }
        except (KeyError, ValueError):
            pass
        return resource

    @staticmethod
    def _is_rate_limited(headers: Mapping[str, str], message: str) -> bool:
        return (
            headers.get("x-ratelimit-remaining") == "0"
            or "retry-after" in headers
            or "rate limit" in message.lower()
        )

    def _wait_seconds(self, headers: Mapping[str, str]) -> float:
        try:
            if "retry-after" in headers:
                return float(headers["retry-after"])
            if headers.get("x-ratelimit-remaining") == "0" and "x-ratelimit-reset" in headers:
                return max(float(headers["x-ratelimit-reset"]) - self._clock(), 0.0)
        except ValueError:
            pass
        return 60.0  # GitHub's advice for secondary limits without a Retry-After header

    def _limit_message(self, resource: str) -> str:
        text = f"GitHub API rate limit reached for the '{resource}' API"
        info = self.rate.get(resource)
        if info:
            reset = datetime.fromtimestamp(info["reset"], tz=timezone.utc)
            minutes = max(int((info["reset"] - self._clock()) // 60) + 1, 1)
            text += (
                f" ({info['remaining']}/{info['limit']} left, resets at {reset:%H:%M} UTC,"
                f" in about {minutes} min)"
            )
        if not self.authenticated:
            text += "; anonymous requests get very low limits, set GITHUB_TOKEN to raise them"
        return text
