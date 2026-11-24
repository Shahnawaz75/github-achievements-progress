"""Tier math and text progress bars. Pure functions, no network."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .tiers import TIER_LABELS


@dataclass(frozen=True)
class TierStatus:
    """Where a count sits on an achievement's tier ladder."""

    count: int
    tier: int  # 0 = not earned yet, otherwise 1..len(thresholds)
    next_threshold: Optional[int]  # None once the top tier is reached
    remaining: int  # how many more are needed for the next tier (0 at the top)
    ratio: float  # 0.0-1.0, count / next_threshold (1.0 at the top)

    @property
    def label(self) -> str:
        """Badge label of the reached tier ("x1".."x4"), or "-" when not earned."""
        return TIER_LABELS[self.tier - 1] if self.tier else "-"

    @property
    def next_label(self) -> Optional[str]:
        """Badge label of the next tier, or None at the top tier."""
        return None if self.next_threshold is None else TIER_LABELS[self.tier]

    @property
    def maxed(self) -> bool:
        """True when there is no higher tier."""
        return self.next_threshold is None


def tier_status(count: int, thresholds: Sequence[int]) -> TierStatus:
    """Compute the tier reached with ``count``. Hitting a threshold exactly reaches that tier."""
    if count < 0:
        raise ValueError("count cannot be negative")
    if not thresholds:
        raise ValueError("this achievement has no thresholds")
    tier = sum(1 for threshold in thresholds if count >= threshold)
    if tier == len(thresholds):
        return TierStatus(count, tier, None, 0, 1.0)
    target = thresholds[tier]
    return TierStatus(count, tier, target, target - count, count / target)


def bar(ratio: float, width: int = 20, ascii_only: bool = False) -> str:
    """Return a text progress bar such as ``[####----------------]``.

    Any progress above zero shows at least one filled cell, so "1 of 128" is visible.
    """
    ratio = min(max(ratio, 0.0), 1.0)
    filled = round(ratio * width)
    if ratio > 0 and filled == 0:
        filled = 1
    full, empty = ("#", "-") if ascii_only else ("█", "░")
    return "[" + full * filled + empty * (width - filled) + "]"
