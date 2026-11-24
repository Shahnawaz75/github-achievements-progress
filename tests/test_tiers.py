"""Tier math, progress bars and the achievement registry."""

import pytest

from github_achievements_progress.progress import bar, tier_status
from github_achievements_progress.tiers import ACHIEVEMENTS, RETIRED, find_achievement

PULL_SHARK = (2, 16, 128, 1024)


@pytest.mark.parametrize("count, tier, target, remaining", [
    (0, 0, 2, 2), (1, 0, 2, 1), (2, 1, 16, 14), (15, 1, 16, 1), (16, 2, 128, 112),
    (18, 2, 128, 110), (127, 2, 128, 1), (128, 3, 1024, 896), (1023, 3, 1024, 1),
])
def test_tier_math_at_and_around_each_threshold(count, tier, target, remaining):
    status = tier_status(count, PULL_SHARK)
    assert (status.tier, status.next_threshold, status.remaining) == (tier, target, remaining)


@pytest.mark.parametrize("count", [1024, 5000])
def test_top_tier_and_beyond_the_top_tier(count):
    status = tier_status(count, PULL_SHARK)
    assert (status.tier, status.label, status.next_label) == (4, "x4", None)
    assert status.maxed and status.remaining == 0 and status.ratio == 1.0


def test_labels_and_ratio():
    status = tier_status(18, PULL_SHARK)
    assert (status.label, status.next_label) == ("x2", "x3")
    assert status.ratio == pytest.approx(18 / 128)
    assert tier_status(0, PULL_SHARK).label == "-"


def test_single_tier_achievement():
    assert tier_status(0, (1,)).tier == 0
    assert tier_status(1, (1,)).maxed
    assert tier_status(7, (1,)).tier == 1


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        tier_status(-1, PULL_SHARK)
    with pytest.raises(ValueError):
        tier_status(1, ())


def test_progress_bar():
    assert bar(0.5, 10, ascii_only=True) == "[#####-----]"
    assert bar(0.001, 10, ascii_only=True) == "[#---------]"  # any progress stays visible
    assert bar(0, 10, ascii_only=True) == "[----------]"
    assert bar(2.0, 4) == "[████]"


def test_registry_matches_the_documented_tiers():
    slugs = [a.slug for a in ACHIEVEMENTS + RETIRED]
    assert len(slugs) == len(set(slugs))
    for ach in ACHIEVEMENTS:
        assert ach.earnable and list(ach.thresholds) == sorted(set(ach.thresholds))
    assert all(not a.earnable and not a.thresholds for a in RETIRED)
    expected = {"pull-shark": (2, 16, 128, 1024), "pair-extraordinaire": (1, 10, 24, 48),
                "galaxy-brain": (2, 8, 16, 32), "starstruck": (16, 128, 512, 4096),
                "quickdraw": (1,), "yolo": (1,), "public-sponsor": (1,)}
    assert {a.slug: a.thresholds for a in ACHIEVEMENTS} == expected


@pytest.mark.parametrize("name, slug", [
    ("Pull Shark", "pull-shark"), ("pull_shark", "pull-shark"), ("PULLSHARK", "pull-shark"),
    ("pair", "pair-extraordinaire"), ("Galaxy-Brain", "galaxy-brain"), ("sponsor", "public-sponsor"),
    ("YOLO", "yolo"), ("arctic", "arctic-code-vault-contributor"),
])
def test_find_achievement_by_name_or_alias(name, slug):
    assert find_achievement(name).slug == slug


def test_unknown_achievement_and_units():
    assert find_achievement("heart-on-your-sleeve") is None
    star = find_achievement("starstruck")
    assert (star.units(1), star.units(2)) == ("star", "stars")
