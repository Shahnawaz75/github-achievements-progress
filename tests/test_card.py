"""The SVG card: valid XML, every achievement, both themes, nothing external."""

import xml.etree.ElementTree as ET

import pytest

from github_achievements_progress.card import THEMES, render_card
from github_achievements_progress.collect import NEEDS_TOKEN, Report, Result
from github_achievements_progress.tiers import ACHIEVEMENTS

SVG = "{http://www.w3.org/2000/svg}"


def sample() -> Report:
    return Report("octo-dev", True, [
        Result("pull-shark", 18), Result("pair-extraordinaire", 1, approximate=True),
        Result("galaxy-brain", reason=NEEDS_TOKEN), Result("starstruck", 5000),
        Result("quickdraw", 2, approximate=True), Result("yolo", 0, approximate=True),
        Result("public-sponsor", 1),
    ])


def texts(svg: str) -> str:
    return " | ".join(el.text or "" for el in ET.fromstring(svg).iter(f"{SVG}text"))


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_card_is_valid_svg_with_every_achievement(theme):
    svg = render_card(sample(), theme)
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG}svg" and root.get("role") == "img"
    content = texts(svg)
    for ach in ACHIEVEMENTS:
        assert ach.name in content
    for expected in ("18 / 128 merged PRs", "~1 / 10 co-authored merged PRs", "needs a token",
                     "top tier", "not yet", "1 sponsorship"):
        assert expected in content


def test_themes_differ_and_use_nothing_external():
    light, dark = render_card(sample(), "light"), render_card(sample(), "dark")
    assert THEMES["light"]["bg"] in light and THEMES["dark"]["bg"] in dark
    for svg in (light, dark):
        assert "<script" not in svg and "@import" not in svg and "href" not in svg
        assert "url(" not in svg and "font-family" in svg


def test_tier_pills():
    svg = render_card(sample())
    assert 'fill="#f9bfa7"' in svg  # x2 (bronze) pill for Pull Shark
    assert 'fill="#fae57e"' in svg  # x4 (gold) pill for Starstruck at 5000 stars
    assert ">earned</text>" in svg  # single-tier Quickdraw / Public Sponsor


def test_user_text_is_escaped():
    svg = render_card(Report("a<b&c", True, [Result("pull-shark", 1)]))
    ET.fromstring(svg)
    assert "a&lt;b&amp;c" in svg


def test_unknown_theme_is_rejected():
    with pytest.raises(ValueError):
        render_card(sample(), "neon")
