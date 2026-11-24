"""Achievement definitions and tier thresholds.

This is the ONE file to edit when GitHub changes its achievement rules.

SOURCE: the thresholds below are COMMUNITY-DOCUMENTED, not official. GitHub does
not publish them. Last checked on 2026-11-24 against:
  - https://github.com/Schweinepriester/github-profile-achievements
  - https://github.com/drknzz/GitHub-Achievements
How to update them: see CONTRIBUTING.md, "How to update tiers when GitHub changes them".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

#: Badge labels for tiers 1-4. GitHub shows no label on tier 1, then x2, x3, x4.
TIER_LABELS: Tuple[str, ...] = ("x1", "x2", "x3", "x4")
#: The community names for the same tiers.
TIER_NAMES: Tuple[str, ...] = ("Default", "Bronze", "Silver", "Gold")

#: Quickdraw: an issue or pull request closed within this many seconds of opening it.
QUICKDRAW_SECONDS = 5 * 60

#: Accepted answers here don't count for Galaxy Brain: GitHub turned achievements off in
#: its own Community discussions on 2024-02-06 (https://github.com/orgs/community/discussions/106536).
EXCLUDED_ANSWER_REPOS: Tuple[str, ...] = ("community/community",)

DELAY_NOTE = "GitHub can take a few hours to a few days to show a new badge or tier."


@dataclass(frozen=True)
class Achievement:
    """One GitHub achievement and the count needed for each tier."""

    slug: str  # the slug GitHub uses in ?tab=achievements&achievement=<slug>
    name: str
    how: str  # one sentence: how to earn it
    unit: str  # what is counted, in plural
    thresholds: Tuple[int, ...] = ()
    earnable: bool = True

    @property
    def tiered(self) -> bool:
        """True when the achievement has x2/x3/x4 tiers."""
        return len(self.thresholds) > 1

    def units(self, count: int) -> str:
        """The unit for ``count``: "1 merged PR" but "2 merged PRs"."""
        return self.unit[:-1] if count == 1 and self.unit.endswith("s") else self.unit


ACHIEVEMENTS: Tuple[Achievement, ...] = (
    Achievement("pull-shark", "Pull Shark", "Open pull requests that get merged.",
                "merged PRs", (2, 16, 128, 1024)),
    Achievement("pair-extraordinaire", "Pair Extraordinaire",
                "Be named in a Co-authored-by: trailer on a commit in a merged pull request.",
                "co-authored merged PRs", (1, 10, 24, 48)),
    Achievement("galaxy-brain", "Galaxy Brain",
                "Have your answer marked as the answer in a Q&A discussion.",
                "accepted answers", (2, 8, 16, 32)),
    Achievement("starstruck", "Starstruck", "Own a repository that gets many stars.",
                "stars", (16, 128, 512, 4096)),
    Achievement("quickdraw", "Quickdraw",
                "Close an issue or pull request within 5 minutes of opening it.",
                "fast closes", (1,)),
    Achievement("yolo", "YOLO", "Merge your own pull request without a code review.",
                "unreviewed self-merged PRs", (1,)),
    Achievement("public-sponsor", "Public Sponsor", "Sponsor someone through GitHub Sponsors.",
                "sponsorships", (1,)),
)

RETIRED: Tuple[Achievement, ...] = (
    Achievement("arctic-code-vault-contributor", "Arctic Code Vault Contributor",
                "Contributed code to repositories in the 2020 GitHub Archive Program.",
                "", earnable=False),
    Achievement("mars-2020-contributor", "Mars 2020 Contributor",
                "Contributed code to repositories used in the Mars 2020 Helicopter Mission.",
                "", earnable=False),
)

_ALIASES: Dict[str, str] = {
    "pr": "pull-shark", "prs": "pull-shark", "shark": "pull-shark",
    "pair": "pair-extraordinaire", "coauthor": "pair-extraordinaire",
    "galaxy": "galaxy-brain", "answers": "galaxy-brain",
    "star": "starstruck", "stars": "starstruck",
    "sponsor": "public-sponsor", "sponsors": "public-sponsor",
    "arctic": "arctic-code-vault-contributor", "mars": "mars-2020-contributor",
}


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def find_achievement(name: str) -> Optional[Achievement]:
    """Look up an achievement by slug, name or alias ("pull-shark", "Pull Shark", "pair")."""
    key = _key(name)
    slug = _ALIASES.get(key, "")
    for ach in ACHIEVEMENTS + RETIRED:
        if key in (_key(ach.slug), _key(ach.name)) or ach.slug == slug:
            return ach
    return None
