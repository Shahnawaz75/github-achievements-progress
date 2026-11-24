"""CLI exit codes, JSON output and error messages."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from conftest import LOGIN, FakeTransport, limit_headers, load, token_routes
from github_achievements_progress import __version__, cli


@pytest.fixture
def run(monkeypatch, capsys):
    def runner(args, routes=None, token="test-token"):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        if token:
            monkeypatch.setenv("GITHUB_TOKEN", token)
        else:
            monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        code = cli.main(args, transport=FakeTransport(token_routes() if routes is None else routes))
        out, err = capsys.readouterr()
        return code, out, err
    return runner


def test_progress_json(run):
    code, out, err = run(["progress", LOGIN, "--json"])
    assert code == 0
    data = json.loads(out)
    results = {a["slug"]: a for a in data["achievements"]}
    assert results["pull-shark"]["tier_label"] == "x2" and results["pull-shark"]["remaining"] == 110
    assert results["pair-extraordinaire"]["approximate"] is True
    assert "test-token" not in out + err


def test_progress_text(run):
    code, out, _ = run(["progress", LOGIN])
    assert code == 0
    assert "Pull Shark" in out and "18/128 merged PRs (110 more for x3)" in out
    assert "community-documented" in out and "Mars 2020 Contributor" in out


def test_why_text(run):
    code, out, _ = run(["why", LOGIN, "Pair Extraordinaire"])
    assert code == 0 and "not linked to any GitHub account" in out


def test_usage_errors_exit_2(run, capsys):
    assert run(["why", LOGIN, "nonsense"])[0] == 2
    code, _, err = run(["progress", "bad/name"])
    assert code == 2 and "not a valid GitHub username" in err
    with pytest.raises(SystemExit) as info:
        cli.main([])
    assert info.value.code == 2


def test_rate_limit_exits_3_with_a_message_and_no_traceback(run):
    limited = (403, load("rate_limited.json"), limit_headers("core", 0, 60, reset_in=3600))
    code, _, err = run(["progress", LOGIN], routes=[("/users/", limited)], token=None)
    assert code == 3 and "rate limit" in err and "Traceback" not in err


def test_unknown_user_exits_1(run):
    code, _, err = run(["why", "ghost", "yolo"], routes=[])
    assert code == 1 and "'ghost' was not found" in err


def test_card_writes_light_and_dark_svg_files(run, tmp_path):
    light, dark = tmp_path / "card.svg", tmp_path / "card-dark.svg"
    code, out, _ = run(["card", LOGIN, "-o", str(light), "--dark-output", str(dark)])
    assert code == 0 and out.count("Wrote") == 2
    assert ET.parse(light).getroot().tag.endswith("svg") and "#0d1117" in dark.read_text(encoding="utf-8")


def test_card_is_not_written_when_rate_limited(run, tmp_path):
    target = tmp_path / "card.svg"
    limited = (403, load("rate_limited.json"), limit_headers("search", 0, 30, reset_in=3600))
    code, _, err = run(["card", LOGIN, "-o", str(target)], routes=[("/search/", limited)] + token_routes())
    assert code == 3 and not target.exists() and "incomplete" in err


def test_unexpected_errors_are_reported_without_a_traceback(run, monkeypatch):
    def boom(collector):
        raise KeyError("surprise")
    monkeypatch.setattr(cli, "collect", boom)
    code, _, err = run(["progress", LOGIN])
    assert code == 1 and "unexpected error" in err and "Traceback" not in err


def test_python_dash_m_entry_point():
    result = subprocess.run([sys.executable, "-m", "github_achievements_progress", "--version"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0 and __version__ in result.stdout
