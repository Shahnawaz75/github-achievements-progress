"""The "why" diagnosis texts."""

import json

from conftest import LOGIN, token_routes
from github_achievements_progress.collect import Collector
from github_achievements_progress.diagnose import diagnose, render_diagnosis
from github_achievements_progress.tiers import find_achievement


def why(collector, name, show_private=False):
    return render_diagnosis(diagnose(LOGIN, find_achievement(name), collector), show_private)


def test_pair_diagnosis_explains_linked_and_unlinked_emails(collector):
    text = why(collector, "pair-extraordinaire")
    assert "linked to @octo-dev: counts for you" in text
    assert "this email is not linked to any GitHub account, so GitHub cannot credit it" in text
    assert "The PR author does not earn it" in text and "1234+octo-dev@users.noreply.github.com" in text
    assert "in merged PR #12" in text and "in a PR that is not merged yet" in text
    assert "a few days" in text


def test_pair_diagnosis_shows_that_coauthors_of_your_commits_get_the_credit(collector):
    text = why(collector, "pair")
    assert "they get the credit, not you" in text
    assert "linked to @pal: GitHub credits them" in text
    assert "Ghost" not in text and "1 item(s) from private repositories are hidden" in text
    assert "GitHub did not read this trailer" in why(collector, "pair", show_private=True)


def test_pull_shark_diagnosis_separates_merged_from_closed(collector):
    text = why(collector, "pull-shark")
    assert "18 merged PRs: these count" in text
    assert "3 closed without merging: these don't count" in text and "2 still open" in text
    assert "x3 needs 128, 110 more to go" in text
    assert "Tiers (community-documented, not official): 2, 16, 128 and 1024 merged PRs." in text


def test_galaxy_brain_and_starstruck_rules(collector):
    galaxy = why(collector, "galaxy-brain")
    assert "marked as the answer in a Q&A" in galaxy and "How do I parse a config file?" in galaxy
    star = why(collector, "starstruck")
    assert "ONE repository" in star and "not your total" in star and "octo-dev/tools" in star


def test_quickdraw_lists_candidates_or_explains_the_criteria(collector, make_client):
    text = why(collector, "quickdraw")
    assert "within 5 minutes" in text and "issue closed after 4m 59s" in text
    client, _ = make_client([("/search/issues", {"total_count": 0, "items": []})] + token_routes())
    empty = why(Collector(client, LOGIN), "quickdraw")
    assert "(none found)" in empty and "not earned yet" in empty


def test_yolo_json_output(collector):
    data = json.loads(json.dumps(diagnose(LOGIN, find_achievement("yolo"), collector).to_dict()))
    assert data["achievement"]["slug"] == "yolo" and data["achievement"]["count"] == 2
    assert data["sections"][0]["items"][1]["repo"] == "(private repository)"


def test_retired_badge_needs_no_api_calls():
    diagnosis = diagnose("anyone", find_achievement("mars"))
    assert diagnosis.summary == "Status: no longer earnable."
    assert "no longer awards" in render_diagnosis(diagnosis)
