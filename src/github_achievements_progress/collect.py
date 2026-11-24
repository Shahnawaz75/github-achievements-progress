"""Collect achievement evidence from the GitHub API and turn it into tier progress.

Everything here is read-only. Each calculator returns a :class:`Result`; one that
cannot run (no token, API error) returns ``count=None`` plus a reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

from .client import GitHubClient, GitHubError, NotFoundError, RateLimitError
from .progress import TierStatus, tier_status
from .tiers import (ACHIEVEMENTS, EXCLUDED_ANSWER_REPOS, QUICKDRAW_SECONDS, RETIRED,
                    Achievement, find_achievement)

NEEDS_TOKEN = "needs a token (set GITHUB_TOKEN): GitHub's GraphQL API has no anonymous access"
HIDDEN_REPO = "(private repository)"
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
TRAILER_RE = re.compile(
    r"^[ \t]*co-authored-by:[ \t]*(?P<name>[^<\n]*?)[ \t]*<(?P<email>[^<>\s]+)>[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
NOREPLY_RE = re.compile(r"^\d+\+(?P<login>[a-z0-9-]+)@users\.noreply\.github\.com$", re.IGNORECASE)

CORE_QUERY = """
query($login: String!, $recent: Int!) {
  user(login: $login) {
    merged: pullRequests(states: MERGED, first: $recent, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes { number title url mergedAt repository { nameWithOwner isPrivate }
              mergedBy { login } reviews { totalCount } }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 3,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { nameWithOwner url stargazerCount isPrivate }
    }
  }
}"""
ANSWERS_QUERY = """
query($login: String!) {
  user(login: $login) {
    answers: repositoryDiscussionComments(onlyAnswers: true, first: 100) {
      totalCount
      nodes { url createdAt discussion { title category { name }
              repository { nameWithOwner isPrivate } } }
    }
  }
}"""
SPONSOR_QUERY = "query($login: String!) { user(login: $login) { sponsoring(first: 1) { totalCount } } }"


@dataclass
class Item:
    """One piece of evidence: a pull request, issue, commit, answer or repository."""

    title: str
    url: str = ""
    repo: str = ""
    when: str = ""
    note: str = ""
    private: bool = False
    details: List[str] = field(default_factory=list)

    def view(self, show_private: bool = False) -> Dict[str, Any]:
        """A dict for output. Private repositories are hidden unless ``show_private``."""
        if self.private and not show_private:
            return {"title": "(hidden)", "url": "", "repo": HIDDEN_REPO, "when": self.when,
                    "note": self.note, "private": True, "details": []}
        return {"title": self.title, "url": self.url, "repo": self.repo, "when": self.when,
                "note": self.note, "private": self.private, "details": list(self.details)}


@dataclass
class Result:
    """Progress evidence for one achievement."""

    slug: str
    count: Optional[int] = None  # None means "could not be checked"
    approximate: bool = False
    detail: str = ""
    reason: str = ""
    items: List[Item] = field(default_factory=list)

    @property
    def achievement(self) -> Achievement:
        ach = find_achievement(self.slug)
        assert ach is not None, self.slug
        return ach

    @property
    def status(self) -> Optional[TierStatus]:
        """Tier status, or None when the count is unknown or the badge is retired."""
        if self.count is None or not self.achievement.thresholds:
            return None
        return tier_status(self.count, self.achievement.thresholds)

    def to_dict(self, show_private: bool = False) -> Dict[str, Any]:
        """JSON-ready view of this result."""
        ach, st = self.achievement, self.status
        return {
            "slug": self.slug, "name": ach.name, "unit": ach.unit, "count": self.count,
            "approximate": self.approximate, "thresholds": list(ach.thresholds),
            "tier": st.tier if st else None, "tier_label": st.label if st else None,
            "next_tier_label": st.next_label if st else None,
            "next_threshold": st.next_threshold if st else None,
            "remaining": st.remaining if st else None,
            "progress": round(st.ratio, 4) if st else None,
            "detail": self.detail, "reason": self.reason,
            "items": [item.view(show_private) for item in self.items],
        }


@dataclass
class Report:
    """Progress for every achievement of one user."""

    login: str
    authenticated: bool
    results: List[Result]
    notes: List[str] = field(default_factory=list)
    rate: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def rate_limited(self) -> bool:
        """True when at least one check stopped because of the rate limit."""
        return any(result.reason.startswith("rate limited") for result in self.results)

    def to_dict(self, show_private: bool = False) -> Dict[str, Any]:
        """JSON-ready view of the whole report."""
        return {
            "user": self.login, "authenticated": self.authenticated, "estimated": True,
            "thresholds_source": "community-documented, not official GitHub documentation",
            "achievements": [result.to_dict(show_private) for result in self.results],
            "no_longer_earnable": [ach.name for ach in RETIRED],
            "notes": self.notes, "rate_limit": self.rate,
        }


@dataclass
class Trailer:
    """A ``Co-authored-by: Name <email>`` line and what GitHub makes of it."""

    name: str
    email: str
    state: str = "unknown"  # linked | unlinked | ignored | unknown
    login: Optional[str] = None  # the account the email belongs to, when linked

    def credits(self, login: str, emails: Sequence[str]) -> bool:
        """True when GitHub (probably) credits ``login`` for this trailer."""
        if self.state == "linked":
            return (self.login or "").lower() == login.lower()
        return self.state == "unknown" and self.email.lower() in {e.lower() for e in emails}


@dataclass
class Commit:
    """A commit found by search, with its trailers and associated pull requests."""

    repo: str
    sha: str
    url: str
    date: str
    message: str
    private: bool = False
    trailers: List[Trailer] = field(default_factory=list)
    pulls: Optional[List[Dict[str, Any]]] = None  # None = not looked up

    @property
    def title(self) -> str:
        """First line of the commit message."""
        return (self.message.splitlines() or [self.sha[:7]])[0][:72]

    def merged_pulls(self) -> List[Dict[str, Any]]:
        """Associated pull requests that were merged."""
        return [pr for pr in self.pulls or [] if pr.get("merged_at")]


def parse_trailers(message: str) -> List[Trailer]:
    """Return every ``Co-authored-by: Name <email>`` trailer (case-insensitive)."""
    return [Trailer(m.group("name").strip(), m.group("email").strip())
            for m in TRAILER_RE.finditer(message or "")]


def parse_time(value: Optional[str]) -> Optional[datetime]:
    """Parse GitHub's ISO 8601 timestamps (``...Z``) on every supported Python."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def seconds_between(start: Optional[str], end: Optional[str]) -> Optional[float]:
    """Seconds from ``start`` to ``end``, or None if either is missing."""
    first, last = parse_time(start), parse_time(end)
    return None if first is None or last is None else (last - first).total_seconds()


def fmt_duration(seconds: float) -> str:
    """Format a short duration: ``42s`` or ``4m 05s``."""
    whole = int(seconds)
    return f"{whole // 60}m {whole % 60:02d}s" if whole >= 60 else f"{whole}s"


def commit_from_search(item: Dict[str, Any]) -> Commit:
    """Build a :class:`Commit` from one ``/search/commits`` result."""
    data, repo = item.get("commit") or {}, item.get("repository") or {}
    message = data.get("message") or ""
    return Commit(repo.get("full_name", ""), item.get("sha", ""), item.get("html_url", ""),
                  ((data.get("committer") or {}).get("date") or "")[:10], message,
                  bool(repo.get("private")), parse_trailers(message))


def resolve_trailers(client: GitHubClient, commits: Sequence[Commit]) -> None:
    """Ask GitHub which account each trailer email belongs to (GraphQL ``Commit.authors``).

    Without a token only ``<id>+<login>@users.noreply.github.com`` can be resolved,
    because such an address always belongs to that account.
    """
    if not client.authenticated:
        for commit in commits:
            for trailer in commit.trailers:
                match = NOREPLY_RE.match(trailer.email)
                if match:
                    trailer.state, trailer.login = "linked", match.group("login")
        return
    todo = [commit for commit in commits if commit.trailers]
    for start in range(0, len(todo), 20):
        batch = todo[start:start + 20]
        decls, fields, variables = [], [], {}
        for i, commit in enumerate(batch):
            owner, _, name = commit.repo.partition("/")
            decls.append(f"$o{i}: String!, $n{i}: String!, $s{i}: GitObjectID!")
            fields.append(f"c{i}: repository(owner: $o{i}, name: $n{i}) {{ object(oid: $s{i}) "
                          "{ ... on Commit { authors(first: 25) { nodes { email user { login } } } } } }")
            variables.update({f"o{i}": owner, f"n{i}": name, f"s{i}": commit.sha})
        data = client.graphql(f"query({', '.join(decls)}) {{ {' '.join(fields)} }}", variables)
        for i, commit in enumerate(batch):
            obj = (data.get(f"c{i}") or {}).get("object") or {}
            nodes = (obj.get("authors") or {}).get("nodes")
            if nodes is None:
                continue  # commit not visible: leave its trailers unresolved
            accounts = {(n.get("email") or "").lower(): (n.get("user") or {}).get("login")
                        for n in nodes}
            for trailer in commit.trailers:
                key = trailer.email.lower()
                if key not in accounts:
                    trailer.state = "ignored"
                elif accounts[key]:
                    trailer.state, trailer.login = "linked", accounts[key]
                else:
                    trailer.state = "unlinked"


class Collector:
    """Fetches and caches the data the calculators need for one user.

    Raises :class:`NotFoundError` when the user does not exist.
    """

    def __init__(self, client: GitHubClient, login: str, *, max_commits: int = 30,
                 pages: int = 2, recent_prs: int = 50) -> None:
        if not LOGIN_RE.match(login):
            raise ValueError(f"'{login}' is not a valid GitHub username")
        self.client = client
        self.max_commits = max_commits if client.authenticated else min(max_commits, 10)
        self.pages, self.recent_prs = pages, recent_prs
        try:
            user = client.rest(f"/users/{login}")
        except NotFoundError:
            raise NotFoundError(f"GitHub user '{login}' was not found") from None
        if user.get("type", "User") != "User":
            raise GitHubError(f"'{login}' is an organization; achievements belong to personal accounts")
        self.login: str = user.get("login") or login
        self.user_id: Optional[int] = user.get("id")
        self.email: Optional[str] = user.get("email")
        self._core: Optional[Dict[str, Any]] = None
        self._coauthored: Optional[List[Commit]] = None
        self._private: Dict[str, bool] = {}
        self.coauthor_matches = 0  # search hits before filtering (set by coauthored_commits)

    def emails(self) -> List[str]:
        """Addresses that identify this user in trailers (noreply forms and public email)."""
        found = [f"{self.user_id}+{self.login}@users.noreply.github.com"] if self.user_id else []
        found.append(f"{self.login}@users.noreply.github.com")
        if self.email:
            found.append(self.email)
        return found

    def core(self) -> Dict[str, Any]:
        """GraphQL: merged pull requests (count and most recent) and most-starred repos."""
        if self._core is None:
            data = self.client.graphql(CORE_QUERY, {"login": self.login, "recent": self.recent_prs})
            if not data.get("user"):
                raise GitHubError("GitHub returned no data for this user")
            self._core = data["user"]
        return self._core

    def search_count(self, query: str) -> int:
        """Total number of issues/PRs matching a search query."""
        return int(self.client.rest("/search/issues", {"q": query, "per_page": 1}).get("total_count") or 0)

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """Newest issues/PRs matching a query, up to ``pages`` pages of 100."""
        found: List[Dict[str, Any]] = []
        for page in range(1, self.pages + 1):
            data = self.client.rest("/search/issues", {"q": query, "sort": "created", "order": "desc",
                                                       "per_page": 100, "page": page})
            items = data.get("items") or []
            found.extend(items)
            if len(items) < 100:
                break
        return found

    def search_commits(self, query: str, per_page: int = 50) -> List[Commit]:
        """Newest commits matching a commit-search query."""
        data = self.client.rest("/search/commits", {"q": query, "sort": "committer-date",
                                                    "order": "desc", "per_page": per_page})
        return [commit_from_search(item) for item in data.get("items") or []]

    def is_private(self, repo: str) -> bool:
        """Whether a repository is private (hidden by default when unsure)."""
        if not self.client.authenticated:
            return False  # anonymous requests only ever see public repositories
        if repo not in self._private:
            try:
                self._private[repo] = bool(self.client.rest(f"/repos/{repo}").get("private"))
            except RateLimitError:
                raise
            except GitHubError:
                self._private[repo] = True
        return self._private[repo]

    def _names_user(self, trailer: Trailer) -> bool:
        """Is this trailer about this user? Same name with another email only counts when that
        email is unlinked (the classic mistake) or linked to this user (a private email)."""
        if trailer.email.lower() in {e.lower() for e in self.emails()}:
            return True
        if trailer.name.lower() != self.login.lower():
            return False
        return trailer.state in ("unlinked", "ignored") or (
            trailer.state == "linked" and (trailer.login or "").lower() == self.login.lower())

    def coauthored_commits(self) -> List[Commit]:
        """Up to ``max_commits`` commits whose trailers name this user, with their pull requests.

        Commits that use one of the user's addresses come first, then name-only matches.
        """
        if self._coauthored is None:
            emails = {e.lower() for e in self.emails()}
            found: Dict[str, Commit] = {}
            for query in [f'"{e}"' for e in self.emails()] + [f'"co-authored-by: {self.login}"']:
                for commit in self.search_commits(query):
                    if any(t.email.lower() in emails or t.name.lower() == self.login.lower()
                           for t in commit.trailers):
                        found.setdefault(commit.sha, commit)
            commits = sorted(found.values(), reverse=True, key=lambda c: (
                any(t.email.lower() in emails for t in c.trailers), c.date))[: self.max_commits]
            try:
                resolve_trailers(self.client, commits)
            except RateLimitError:
                raise
            except GitHubError:
                pass  # trailers stay "unknown"; counting falls back to the known addresses
            commits = [c for c in commits if any(self._names_user(t) for t in c.trailers)]
            for commit in commits:
                try:
                    commit.pulls = self.client.rest(f"/repos/{commit.repo}/commits/{commit.sha}/pulls")
                except RateLimitError:
                    raise
                except GitHubError:
                    commit.pulls = []
            self.coauthor_matches = len(found)
            self._coauthored = commits
        return self._coauthored

    def authored_with_coauthors(self, limit: int = 5) -> List[Commit]:
        """Recent commits this user authored that name co-authors (they get the credit)."""
        commits = [c for c in self.search_commits(f'author:{self.login} "co-authored-by"', 20)
                   if c.trailers][:limit]
        resolve_trailers(self.client, commits)
        return commits


def pull_shark(c: Collector) -> Result:
    """Merged pull requests opened by the user."""
    if c.client.authenticated:
        count = int(c.core()["merged"]["totalCount"])
    else:
        count = c.search_count(f"author:{c.login} type:pr is:merged")
    return Result("pull-shark", count)


def pair_extraordinaire(c: Collector) -> Result:
    """Distinct merged PRs containing a commit whose trailer credits the user (approximate)."""
    emails, merged = c.emails(), {}
    commits = c.coauthored_commits()
    for commit in commits:
        if not any(t.credits(c.login, emails) for t in commit.trailers):
            continue
        for pr in commit.merged_pulls():
            merged.setdefault(pr.get("html_url", ""), Item(
                f"#{pr.get('number')} {pr.get('title', '')}", pr.get("html_url", ""), commit.repo,
                (pr.get("merged_at") or "")[:10], "merged", commit.private,
                [f"opened by @{(pr.get('user') or {}).get('login', '?')}"]))
    detail = f"commits naming you as co-author: {len(commits)} checked"
    if c.coauthor_matches > c.max_commits:
        detail += f" of {c.coauthor_matches} search hits (raise --max-commits to check more)"
    return Result("pair-extraordinaire", len(merged), True, detail, items=list(merged.values()))


def galaxy_brain(c: Collector) -> Result:
    """Discussion comments marked as the answer (GitHub Community answers excluded)."""
    if not c.client.authenticated:
        return Result("galaxy-brain", reason=NEEDS_TOKEN)
    user = c.client.graphql(ANSWERS_QUERY, {"login": c.login}).get("user") or {}
    answers = user.get("answers") or {}
    nodes, items, excluded = answers.get("nodes") or [], [], 0
    for node in nodes:
        discussion = node.get("discussion") or {}
        repo = discussion.get("repository") or {}
        name = repo.get("nameWithOwner", "")
        skip = name.lower() in EXCLUDED_ANSWER_REPOS
        excluded += int(skip)
        note = "GitHub Community: does not count" if skip else (discussion.get("category") or {}).get("name", "")
        items.append(Item(discussion.get("title", ""), node.get("url", ""), name,
                          (node.get("createdAt") or "")[:10], note, bool(repo.get("isPrivate"))))
    total = int(answers.get("totalCount") or 0)
    detail = f"answers in GitHub Community discussions, not counted: {excluded}" if excluded else ""
    return Result("galaxy-brain", max(total - excluded, 0), total > len(nodes), detail, items=items)


def starstruck(c: Collector) -> Result:
    """Stars on the user's most-starred non-fork repository (private names are masked)."""
    if c.client.authenticated:
        items = [Item(r["nameWithOwner"], r["url"], r["nameWithOwner"], note=f"{r['stargazerCount']} stars",
                      private=bool(r.get("isPrivate"))) for r in c.core()["repositories"]["nodes"]]
        stars = [int(r["stargazerCount"]) for r in c.core()["repositories"]["nodes"]]
    else:
        data = c.client.rest("/search/repositories", {"q": f"user:{c.login}", "sort": "stars",
                                                      "order": "desc", "per_page": 3})
        found = data.get("items") or []
        items = [Item(r["full_name"], r["html_url"], r["full_name"], note=f"{r['stargazers_count']} stars")
                 for r in found]
        stars = [int(r["stargazers_count"]) for r in found]
    if not items:
        return Result("starstruck", 0, detail="no repositories found")
    top = HIDDEN_REPO if items[0].private else items[0].repo
    return Result("starstruck", stars[0], detail=f"most-starred repo: {top}", items=items)


def quickdraw(c: Collector) -> Result:
    """Recent issues/PRs by the user that were closed within 5 minutes (approximate)."""
    scanned = c.search_items(f"author:{c.login} is:closed")
    items = []
    for issue in scanned:
        seconds = seconds_between(issue.get("created_at"), issue.get("closed_at"))
        if seconds is None or seconds > QUICKDRAW_SECONDS:
            continue
        pull = issue.get("pull_request")
        kind = "issue closed" if pull is None else ("PR merged" if pull.get("merged_at") else "PR closed")
        repo = "/".join((issue.get("repository_url") or "").split("/")[-2:])
        items.append(Item(f"#{issue.get('number')} {issue.get('title', '')}", issue.get("html_url", ""),
                          repo, (issue.get("created_at") or "")[:10],
                          f"{kind} after {fmt_duration(seconds)}", c.is_private(repo)))
    detail = f"your most recent closed issues and PRs scanned: {len(scanned)}"
    return Result("quickdraw", len(items), True, detail, items=items)


def yolo(c: Collector) -> Result:
    """Recent PRs by the user, merged by the user, with zero reviews (approximate)."""
    if not c.client.authenticated:
        return Result("yolo", reason=NEEDS_TOKEN)
    nodes = c.core()["merged"]["nodes"] or []
    items = []
    for pr in nodes:
        merger = (pr.get("mergedBy") or {}).get("login") or ""
        if merger.lower() == c.login.lower() and not (pr.get("reviews") or {}).get("totalCount"):
            repo = pr.get("repository") or {}
            items.append(Item(f"#{pr.get('number')} {pr.get('title', '')}", pr.get("url", ""),
                              repo.get("nameWithOwner", ""), (pr.get("mergedAt") or "")[:10],
                              "merged by you, 0 reviews", bool(repo.get("isPrivate"))))
    return Result("yolo", len(items), True, f"your most recent merged PRs checked: {len(nodes)}", items=items)


def public_sponsor(c: Collector) -> Result:
    """Sponsorships the user has that this token can see."""
    if not c.client.authenticated:
        return Result("public-sponsor", reason=NEEDS_TOKEN)
    user = c.client.graphql(SPONSOR_QUERY, {"login": c.login}).get("user") or {}
    return Result("public-sponsor", int((user.get("sponsoring") or {}).get("totalCount") or 0))


CALCULATORS: Dict[str, Callable[[Collector], Result]] = {
    "pull-shark": pull_shark, "pair-extraordinaire": pair_extraordinaire,
    "galaxy-brain": galaxy_brain, "starstruck": starstruck, "quickdraw": quickdraw,
    "yolo": yolo, "public-sponsor": public_sponsor,
}


def run_calculator(collector: Collector, slug: str) -> Result:
    """Run one calculator; API problems become a Result with a reason instead of an exception."""
    try:
        return CALCULATORS[slug](collector)
    except RateLimitError as err:
        return Result(slug, reason=f"rate limited: {err}")
    except GitHubError as err:
        return Result(slug, reason=f"could not check: {err}")


def collect(collector: Collector) -> Report:
    """Compute progress for every earnable achievement."""
    results = [run_calculator(collector, ach.slug) for ach in ACHIEVEMENTS]
    notes = []
    if not collector.client.authenticated:
        notes.append("No token: public data only and low rate limits. Galaxy Brain, YOLO and "
                     "Public Sponsor need GITHUB_TOKEN (for example: export GITHUB_TOKEN=$(gh auth token)).")
    return Report(collector.login, collector.client.authenticated, results, notes,
                  collector.client.rate_summary())
