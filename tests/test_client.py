"""The read-only HTTP client: auth header, rate limits and error handling."""

import urllib.error

import pytest

from conftest import load, limit_headers
from github_achievements_progress import client as client_module
from github_achievements_progress.client import (AuthError, GitHubClient, GitHubError, NetworkError,
                                                 NotFoundError, RateLimitError)


def test_rest_sends_the_token_but_never_shows_it(make_client):
    client, transport = make_client([("/users/octo-dev", {"login": "octo-dev"})], token="secret-123")
    assert client.rest("/users/octo-dev") == {"login": "octo-dev"}
    request = transport.requests[0]
    assert request["method"] == "GET"
    assert request["headers"]["Authorization"] == "Bearer secret-123"
    assert "secret-123" not in repr(client)


def test_anonymous_client_sends_no_authorization_header(make_client):
    client, transport = make_client([("/users/", {"login": "x"})], token=None)
    client.rest("/users/x")
    assert "Authorization" not in transport.requests[0]["headers"]
    assert not client.authenticated


def test_rate_limit_budget_is_tracked_per_resource(make_client):
    client, _ = make_client([("/search/issues", (200, {"total_count": 1}, limit_headers("search", 27, 30)))])
    client.rest("/search/issues", {"q": "author:x"})
    summary = client.rate_summary()["search"]
    assert (summary["remaining"], summary["limit"]) == (27, 30)
    assert summary["reset"].endswith("Z")


def test_primary_rate_limit_with_a_far_reset_fails_fast_with_a_clear_message(make_client):
    response = (403, load("rate_limited.json"), limit_headers("core", 0, 60, reset_in=1800))
    client, transport = make_client([("/users/", response)], token=None)
    with pytest.raises(RateLimitError) as info:
        client.rest("/users/octo-dev")
    message = str(info.value)
    assert "'core'" in message and "0/60 left" in message and "GITHUB_TOKEN" in message
    assert len(transport.requests) == 1  # it did not sit and wait for half an hour


def test_secondary_rate_limit_backs_off_and_retries(make_client):
    waits = []
    responses = [(403, {"message": "You have exceeded a secondary rate limit."}, {"Retry-After": "3"}),
                 (200, {"ok": True}, {})]
    client, transport = make_client([("/search/", responses)], sleep=waits.append)
    assert client.rest("/search/issues", {"q": "x"}) == {"ok": True}
    assert waits == [3.0] and len(transport.requests) == 2


def test_graphql_needs_a_token(make_client):
    client, transport = make_client([], token=None)
    with pytest.raises(AuthError):
        client.graphql("query { viewer { login } }")
    assert transport.requests == []


def test_graphql_errors_become_clear_exceptions(make_client):
    client, _ = make_client([("viewer", load("graphql_rate_limited.json"))])
    with pytest.raises(RateLimitError):
        client.graphql("query { viewer { login } }")
    client, _ = make_client([("viewer", load("graphql_forbidden.json"))])
    with pytest.raises(GitHubError, match="not accessible"):
        client.graphql("query { viewer { login } }")


def test_http_errors_map_to_exception_types(make_client):
    routes = [("/bad", (401, {"message": "Bad credentials"}, {})), ("/boom", (500, {"message": "Oops"}, {}))]
    client, _ = make_client(routes, token="secret-xyz")
    with pytest.raises(AuthError) as info:
        client.rest("/bad")
    assert "secret-xyz" not in str(info.value)
    with pytest.raises(NotFoundError):
        client.rest("/missing")
    with pytest.raises(GitHubError, match="500"):
        client.rest("/boom")


def test_network_failure_is_wrapped(monkeypatch):
    def offline(request, timeout):
        raise urllib.error.URLError("no route to host")
    monkeypatch.setattr(client_module.urllib.request, "urlopen", offline)
    with pytest.raises(NetworkError, match="could not reach GitHub"):
        GitHubClient("t").rest("/users/octo-dev")
