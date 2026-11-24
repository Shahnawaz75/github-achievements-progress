"""Diagnosis ("why") mode: the rules for one achievement plus the evidence we found."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .client import GitHubError, RateLimitError
from .collect import Collector, Commit, Item, Result, Trailer, parse_time, run_calculator
from .tiers import DELAY_NOTE, Achievement

RULES: Dict[str, List[str]] = {
    "pull-shark": [
        "Counts pull requests you opened that were merged. Closed-without-merge and open PRs don't count.",
    ],
    "pair-extraordinaire": [
        "GitHub credits the people named in Co-authored-by: trailers on commits in a merged PR. "
        "The PR author does not earn it from their own PR.",
        "The trailer email must belong to the co-author's GitHub account. "
        "Your noreply address always works: {noreply}",
        "Format: 'Co-authored-by: Name <email>' on its own line at the very end of the commit "
        "message, after a blank line. For squash merges, keep it in the final commit message.",
    ],
    "galaxy-brain": [
        "Counts your discussion comments that were marked as the answer in a Q&A (answerable) category.",
        "Only the discussion author or a maintainer can mark an answer; comments and upvotes don't count.",
        "Answers in GitHub's own Community discussions (github.com/orgs/community) don't count: "
        "GitHub turned achievements off there in February 2024.",
    ],
    "starstruck": [
        "Counts the stars on ONE repository you own, not your total stars across repositories.",
        "This tool checks non-fork repositories owned by your personal account that the token can see.",
    ],
    "quickdraw": [
        "Close an issue or pull request within 5 minutes of opening it.",
        "PRs merged within 5 minutes are listed too: merging closes a PR, and community reports say it counts.",
    ],
    "yolo": [
        "Merge your own pull request without anyone reviewing it.",
        "A PR that received any review (approve, comment or request changes) does not qualify.",
    ],
    "public-sponsor": [
        "Sponsor any developer or organization through GitHub Sponsors (monthly or one-time).",
        "Private sponsorships are hidden from others, and past one-time sponsorships may not show in the API.",
    ],
}


@dataclass
class Diagnosis:
    """Everything ``why`` shows for one achievement."""

    login: str
    result: Result
    rules: List[str]
    facts: List[str] = field(default_factory=list)
    sections: List[Tuple[str, List[Item]]] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """One status line, e.g. "18 merged PRs -> tier x2 (estimated); x3 needs 128..."."""
        result, ach, st = self.result, self.result.achievement, self.result.status
        if not ach.earnable:
            return "Status: no longer earnable."
        if st is None:
            return f"Status: could not check ({result.reason})."
        approx = " (approximate)" if result.approximate else ""
        if not ach.tiered:
            verdict = "likely earned" if st.tier else "not earned yet"
            return f"Status: {st.count} {ach.units(st.count)} found{approx}: {verdict} (estimated)."
        reached = f"tier {st.label}" if st.tier else "not earned yet"
        nxt = "top tier reached" if st.maxed else f"{st.next_label} needs {st.next_threshold}, {st.remaining} more to go"
        return f"Status: {st.count} {ach.units(st.count)}{approx} -> {reached} (estimated); {nxt}."

    def to_dict(self, show_private: bool = False) -> Dict[str, Any]:
        """JSON-ready view."""
        return {
            "user": self.login, "achievement": self.result.to_dict(show_private),
            "summary": self.summary, "rules": self.rules, "facts": self.facts,
            "sections": [{"title": title, "items": [i.view(show_private) for i in items]}
                         for title, items in self.sections],
            "note": DELAY_NOTE,
        }


def explain_trailer(trailer: Trailer, login: str) -> str:
    """Say in plain words what GitHub does with one Co-authored-by trailer."""
    if trailer.state == "linked":
        if (trailer.login or "").lower() == login.lower():
            return f"linked to @{trailer.login}: counts for you"
        return f"linked to @{trailer.login}: GitHub credits them"
    if trailer.state == "unlinked":
        return "this email is not linked to any GitHub account, so GitHub cannot credit it"
    if trailer.state == "ignored":
        return "GitHub did not read this trailer; check the format and keep it at the very end"
    return "could not check without a token"


def _commit_item(commit: Commit, login: str, with_prs: bool) -> Item:
    note = ""
    if with_prs:
        merged = commit.merged_pulls()
        if merged:
            note = "in merged PR " + ", ".join(f"#{pr.get('number')}" for pr in merged)
        elif commit.pulls:
            note = "in a PR that is not merged yet"
        else:
            note = "no pull request found (pushed directly?)"
    details = [f"Co-authored-by: {t.name} <{t.email}> -> {explain_trailer(t, login)}" for t in commit.trailers]
    return Item(f"{commit.title} ({commit.sha[:7]})", commit.url, commit.repo, commit.date, note,
                commit.private, details)


def _recent(day: str, days: int = 3) -> bool:
    when = parse_time(f"{day}T00:00:00Z")
    return when is not None and datetime.now(timezone.utc) - when <= timedelta(days=days)


def _pull_shark(c: Collector, d: Diagnosis) -> None:
    closed = c.search_count(f"author:{c.login} type:pr is:closed is:unmerged")
    still_open = c.search_count(f"author:{c.login} type:pr is:open")
    d.facts += [f"{d.result.count} merged PRs: these count",
                f"{closed} closed without merging: these don't count",
                f"{still_open} still open: they count once merged"]


def _pair(c: Collector, d: Diagnosis) -> None:
    commits = c.coauthored_commits()
    if not commits:
        d.facts.append("No commit found that names you in a Co-authored-by: trailer. "
                       "Ask your co-author to add your noreply address.")
    d.sections.append(("Commits that name you as co-author",
                       [_commit_item(commit, c.login, True) for commit in commits[:10]]))
    newest = max((item.when for item in d.result.items), default="")
    if newest and _recent(newest):
        d.facts.append(f"Your newest co-authored PR was merged on {newest}: give GitHub a few days to show it.")
    d.sections.append(("Recent commits you authored with co-authors (they get the credit, not you)",
                       [_commit_item(commit, c.login, False) for commit in c.authored_with_coauthors()]))


def _section(title: str) -> Callable[[Collector, Diagnosis], None]:
    def add(c: Collector, d: Diagnosis) -> None:
        d.sections.append((title, d.result.items))
    return add


def _sponsor(c: Collector, d: Diagnosis) -> None:
    d.facts.append(f"You are sponsoring {d.result.count} account(s) that this token can see.")


EXTRA: Dict[str, Callable[[Collector, Diagnosis], None]] = {
    "pull-shark": _pull_shark,
    "pair-extraordinaire": _pair,
    "galaxy-brain": _section("Accepted answers"),
    "starstruck": _section("Your most-starred repositories"),
    "quickdraw": _section("Candidates: closed within 5 minutes of opening"),
    "yolo": _section("Candidates: merged by you with 0 reviews"),
    "public-sponsor": _sponsor,
}


def diagnose(login: str, ach: Achievement, collector: Optional[Collector] = None) -> Diagnosis:
    """Build the diagnosis for one achievement. Retired badges need no API calls."""
    if not ach.earnable or collector is None:
        return Diagnosis(login, Result(ach.slug, reason="no longer earnable"),
                         [ach.how, "GitHub no longer awards this achievement."])
    result = run_calculator(collector, ach.slug)
    rules = [rule.format(noreply=collector.emails()[0]) for rule in RULES[ach.slug]]
    if ach.tiered:  # generated from tiers.py, so the text never disagrees with the math
        steps = ", ".join(str(t) for t in ach.thresholds[:-1])
        rules.append(f"Tiers (community-documented, not official): {steps} and {ach.thresholds[-1]} {ach.unit}.")
    d = Diagnosis(collector.login, result, rules)
    if result.detail:
        d.facts.append(result.detail)
    if result.count is not None:
        try:
            EXTRA[ach.slug](collector, d)
        except RateLimitError as err:
            d.facts.append(f"Stopped early: {err}")
        except GitHubError as err:
            d.facts.append(f"Some details could not be loaded: {err}")
    return d


def render_diagnosis(d: Diagnosis, show_private: bool = False) -> str:
    """Plain-text output of ``why``."""
    lines = [f"{d.result.achievement.name} for @{d.login}", d.summary, "", "How it works:"]
    lines += [f"  - {rule}" for rule in d.rules]
    if d.facts:
        lines += ["", "What we found:"] + [f"  - {fact}" for fact in d.facts]
    hidden = 0
    for title, items in d.sections:
        lines += ["", f"{title}:"]
        if not items:
            lines.append("  (none found)")
        for item in items:
            view = item.view(show_private)
            hidden += int(item.private and not show_private)
            meta = ", ".join(part for part in (view["repo"], view["when"]) if part)
            lines.append(f"  - {view['title']} [{meta}]" + (f" {view['note']}" if view["note"] else ""))
            lines += [f"      {detail}" for detail in view["details"]]
            if view["url"]:
                lines.append(f"      {view['url']}")
    if hidden:
        lines += ["", f"{hidden} item(s) from private repositories are hidden; add --show-private to see them."]
    lines += ["", DELAY_NOTE]
    return "\n".join(lines)
