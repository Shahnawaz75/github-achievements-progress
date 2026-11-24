"""Shared helpers: a fake HTTP transport that answers from JSON fixtures (no network)."""

from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pytest

from github_achievements_progress.client import GitHubClient
from github_achievements_progress.collect import Collector

FIXTURES = Path(__file__).parent / "fixtures"
LOGIN = "octo-dev"


def load(name: str) -> Any:
    """Load one JSON fixture."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def limit_headers(resource: str, remaining: int, limit: int = 60, reset_in: int = 3600) -> Dict[str, str]:
    """Rate-limit headers as GitHub sends them."""
    return {"X-RateLimit-Resource": resource, "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining), "X-RateLimit-Reset": str(int(time.time()) + reset_in)}


class FakeTransport:
    """Answers each request with the first route whose needle occurs in "METHOD url body".

    A route's response is a payload (status 200), a ``(status, payload, headers)``
    tuple, or a list of those that is consumed in order (the last one repeats).
    """

    def __init__(self, routes: Sequence[Tuple[str, Any]]) -> None:
        self.routes = [(needle, list(resp) if isinstance(resp, list) and resp and isinstance(resp[0], tuple)
                        else resp) for needle, resp in routes]
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, method: str, url: str, headers: Mapping[str, str], body: Optional[bytes],
                 timeout: float) -> Tuple[int, Dict[str, str], bytes]:
        text = f"{method} {urllib.parse.unquote_plus(url)} {body.decode('utf-8') if body else ''}"
        self.requests.append({"method": method, "url": url, "headers": dict(headers), "text": text})
        for needle, response in self.routes:
            if needle in text:
                if isinstance(response, list) and response and isinstance(response[0], tuple):
                    response = response.pop(0) if len(response) > 1 else response[0]
                status, payload, extra = response if isinstance(response, tuple) else (200, response, {})
                return status, dict(extra), json.dumps(payload).encode("utf-8")
        return 404, {}, b'{"message": "Not Found"}'


def token_routes() -> List[Tuple[str, Any]]:
    """Routes for the full happy path of user ``octo-dev``."""
    return [
        ("/users/octo-dev", load("user.json")),
        ("merged: pullRequests", load("graphql_core.json")),
        ("onlyAnswers", load("graphql_answers.json")),
        ("sponsoring", load("graphql_sponsoring.json")),
        ('"s0": "eeeeeeee', load("graphql_authored_authors.json")),
        ('"s0": "aaaaaaaa', load("graphql_coauthor_authors.json")),
        ("/search/commits?q=author:octo-dev", load("search_commits_authored.json")),
        ("/search/commits", load("search_commits_coauthor.json")),
        ("/commits/cccccccc", load("commit_pulls_open.json")),
        ("/pulls", load("commit_pulls_merged.json")),
        ("is:closed is:unmerged", {"total_count": 3, "items": []}),
        ("type:pr is:open", {"total_count": 2, "items": []}),
        ("type:pr is:merged", {"total_count": 14, "items": []}),
        ("/search/issues", load("search_closed.json")),
        ("/search/repositories", load("search_repos.json")),
        ("/repos/octo-dev/secret", {"private": True}),
        ("/repos/", {"private": False}),
    ]


@pytest.fixture
def make_client():
    """Factory: ``make_client(routes, token=...) -> (GitHubClient, FakeTransport)``."""
    def factory(routes: Sequence[Tuple[str, Any]], token: Optional[str] = "test-token", **kwargs: Any):
        transport = FakeTransport(routes)
        client = GitHubClient(token, transport=transport, sleep=kwargs.pop("sleep", lambda s: None), **kwargs)
        return client, transport
    return factory


@pytest.fixture
def collector(make_client) -> Collector:
    """A Collector for ``octo-dev`` with a token, backed by the fixtures."""
    client, _ = make_client(token_routes())
    return Collector(client, LOGIN)
