"""Calculators for each achievement, against mocked API responses."""

import json

import pytest

from conftest import LOGIN, limit_headers, load, token_routes
from github_achievements_progress.client import GitHubError, NotFoundError
from github_achievements_progress.collect import (HIDDEN_REPO, Collector, Commit, Trailer, collect,
                                                  galaxy_brain, pair_extraordinaire, parse_trailers,
                                                  public_sponsor, pull_shark, quickdraw, resolve_trailers,
                                                  starstruck, yolo)
from github_achievements_progress.tiers import ACHIEVEMENTS


def by_slug(report):
    return {result.slug: result for result in report.results}


def test_pull_shark_from_merged_pr_count(collector):
    result = pull_shark(collector)
    assert result.count == 18 and result.status.label == "x2" and result.status.remaining == 110


def test_starstruck_uses_the_single_most_starred_repo(collector):
    result = starstruck(collector)
    assert result.count == 20 and result.status.label == "x1" and result.status.remaining == 108
    assert result.detail == "most-starred repo: octo-dev/tools"


def test_starstruck_hides_a_private_top_repo(make_client):
    core = load("graphql_core.json")
    core["data"]["user"]["repositories"]["nodes"][0]["isPrivate"] = True
    client, _ = make_client([("merged: pullRequests", core)] + token_routes())
    result = starstruck(Collector(client, LOGIN))
    assert result.count == 20 and HIDDEN_REPO in result.detail
    assert result.items[0].view()["repo"] == HIDDEN_REPO
    assert result.items[0].view(show_private=True)["repo"] == "octo-dev/tools"


def test_galaxy_brain_skips_github_community_answers(collector):
    result = galaxy_brain(collector)
    assert result.count == 2 and result.status.tier == 1  # exactly on the first threshold
    assert "not counted: 1" in result.detail


def test_public_sponsor(collector):
    assert public_sponsor(collector).status.tier == 1


def test_yolo_counts_only_unreviewed_prs_merged_by_the_user(collector):
    result = yolo(collector)
    assert [item.title for item in result.items] == ["#3 Fix typo", "#7 Internal change"]
    assert result.approximate and result.items[1].view()["title"] == "(hidden)"


def test_quickdraw_five_minute_boundary(collector):
    result = quickdraw(collector)
    assert result.count == 2 and result.approximate
    assert [item.note for item in result.items] == ["issue closed after 4m 59s", "PR merged after 5m 00s"]


def test_pair_extraordinaire_counts_distinct_merged_prs(collector):
    result = pair_extraordinaire(collector)
    assert result.count == 1 and result.status.label == "x1"
    assert result.items[0].url == "https://github.com/friend/app/pull/12"
    assert result.detail == "commits naming you as co-author: 3 checked"


def test_coauthor_search_dedupes_and_filters_other_people(collector):
    commits = collector.coauthored_commits()
    # Own addresses first (a, c), then same-name matches (b). "d" has no trailer, and "9" uses
    # the same name but an email that belongs to a different account, so it is not about us.
    assert [commit.sha[0] for commit in commits] == ["a", "c", "b"]
    assert collector.coauthor_matches == 4


def test_trailer_resolution_linked_vs_unlinked_email(collector):
    states = {c.sha[0]: [(t.email, t.state, t.login) for t in c.trailers] for c in collector.coauthored_commits()}
    assert states["a"] == [("1234+octo-dev@users.noreply.github.com", "linked", "octo-dev")]
    assert states["b"] == [("octo@old-mail.example", "unlinked", None)]
    assert states["c"][1] == ("99+pal@users.noreply.github.com", "linked", "pal")


def test_parse_trailers_formats():
    message = ("Title\n\nBody\n\nCo-authored-by: Ann Lee <ann@example.com>\n"
               "co-authored-by:bob<bob@example.com>\nCo-Authored-By: no email here\n")
    assert [(t.name, t.email) for t in parse_trailers(message)] == [("Ann Lee", "ann@example.com"),
                                                                    ("bob", "bob@example.com")]


def test_without_a_token_only_noreply_addresses_resolve(make_client):
    client, transport = make_client([], token=None)
    commit = Commit("o/r", "s" * 40, "", "2026-11-01", "msg",
                    trailers=[Trailer("pal", "99+pal@users.noreply.github.com"), Trailer("x", "x@example.com")])
    resolve_trailers(client, [commit])
    assert [(t.state, t.login) for t in commit.trailers] == [("linked", "pal"), ("unknown", None)]
    assert transport.requests == []


def test_anonymous_mode_uses_rest_and_says_what_needs_a_token(make_client):
    client, transport = make_client(token_routes(), token=None)
    collector = Collector(client, LOGIN)
    report = collect(collector)
    results = by_slug(report)
    assert results["pull-shark"].count == 14 and results["starstruck"].count == 20
    for slug in ("galaxy-brain", "yolo", "public-sponsor"):
        assert results[slug].count is None and "token" in results[slug].reason
    assert not any("/graphql" in request["url"] for request in transport.requests)
    assert collector.max_commits == 10 and "GITHUB_TOKEN" in report.notes[0]


def test_one_failing_check_does_not_break_the_others(make_client):
    client, _ = make_client([("sponsoring", load("graphql_forbidden.json"))] + token_routes())
    results = by_slug(collect(Collector(client, LOGIN)))
    assert results["public-sponsor"].count is None
    assert results["public-sponsor"].reason.startswith("could not check")
    assert results["pull-shark"].count == 18


def test_rate_limit_marks_the_affected_checks_only(make_client):
    limited = (403, load("rate_limited.json"), limit_headers("search", 0, 30, reset_in=3600))
    client, _ = make_client([("/search/", limited)] + token_routes())
    report = collect(Collector(client, LOGIN))
    results = by_slug(report)
    assert report.rate_limited and results["quickdraw"].reason.startswith("rate limited")
    assert results["pull-shark"].count == 18  # GraphQL still answered
    assert report.rate["search"]["remaining"] == 0


def test_unknown_user_organization_and_bad_name(make_client):
    client, _ = make_client([("/users/acme", {"login": "acme", "type": "Organization", "id": 9})])
    with pytest.raises(NotFoundError, match="ghost"):
        Collector(client, "ghost")
    with pytest.raises(GitHubError, match="organization"):
        Collector(client, "acme")
    with pytest.raises(ValueError):
        Collector(client, "bad/name")


def test_report_json_lists_every_achievement(collector):
    data = json.loads(json.dumps(collect(collector).to_dict()))
    assert data["estimated"] is True and data["user"] == LOGIN
    assert [a["slug"] for a in data["achievements"]] == [a.slug for a in ACHIEVEMENTS]
    pull = data["achievements"][0]
    assert (pull["tier_label"], pull["next_tier_label"], pull["remaining"]) == ("x2", "x3", 110)
