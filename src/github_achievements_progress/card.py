"""Render the progress card as one self-contained SVG for a profile README.

GitHub shows README images through its image proxy as ``<img>``, so the SVG
uses no external fonts, images or scripts: only inline styles and a system
font stack. Only counts and tiers are drawn, never private repository names.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from xml.sax.saxutils import escape

from .collect import Report, Result

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
THEMES: Dict[str, Dict[str, str]] = {
    "light": {"bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328", "muted": "#59636e",
              "track": "#eaeef2", "fill": "#1f883d"},
    "dark": {"bg": "#0d1117", "border": "#30363d", "text": "#f0f6fc", "muted": "#9198a1",
             "track": "#21262d", "fill": "#3fb950"},
}
#: (background, text) of the tier pill; x2-x4 use GitHub's bronze, silver and gold label colors.
PILLS: Dict[int, Tuple[str, str]] = {1: ("#ddf4ff", "#0550ae"), 2: ("#f9bfa7", "#5c2410"),
                           3: ("#e1e4e4", "#32383f"), 4: ("#fae57e", "#4d3d00")}
EARNED = ("#dafbe1", "#116329")
WIDTH, TOP, ROW, BOTTOM, PILL_X = 495, 72, 38, 34, 180


def value_text(result: Result) -> str:
    """The short text on the right of a row, e.g. ``18 / 128 merged PRs``."""
    ach, st = result.achievement, result.status
    if st is None:
        return "needs a token" if "token" in result.reason else "not available"
    approx = "~" if result.approximate else ""
    if not ach.tiered:
        return f"{approx}{st.count} {ach.units(st.count)}" if st.tier else "not yet"
    if st.maxed:
        return f"{approx}{st.count} {ach.units(st.count)} · top tier"
    return f"{approx}{st.count} / {st.next_threshold} {ach.unit}"


def _row(result: Result, y: int, colors: Dict[str, str]) -> List[str]:
    ach, st = result.achievement, result.status
    parts = [
        f'<text class="n" x="24" y="{y + 12}">{escape(ach.name)}</text>',
        f'<text class="v" x="{WIDTH - 24}" y="{y + 12}" text-anchor="end">{escape(value_text(result))}</text>',
    ]
    if st is not None and st.tier:
        label, (bg, fg), width = (st.label, PILLS[st.tier], 26) if ach.tiered else ("earned", EARNED, 46)
        parts += [
            f'<rect x="{PILL_X}" y="{y}" width="{width}" height="16" rx="8" fill="{bg}"/>',
            f'<text class="p" x="{PILL_X + width // 2}" y="{y + 11.5}" text-anchor="middle" '
            f'fill="{fg}">{label}</text>',
        ]
    track = WIDTH - 48
    parts.append(f'<rect x="24" y="{y + 20}" width="{track}" height="6" rx="3" fill="{colors["track"]}"/>')
    ratio = st.ratio if st is not None else 0.0
    if ratio > 0:
        parts.append(f'<rect x="24" y="{y + 20}" width="{max(track * ratio, 6):.1f}" height="6" '
                     f'rx="3" fill="{colors["fill"]}"/>')
    return parts


def render_card(report: Report, theme: str = "light") -> str:
    """Return the SVG card (light or dark theme) as a string."""
    if theme not in THEMES:
        raise ValueError(f"unknown theme '{theme}' (use light or dark)")
    c = THEMES[theme]
    height = TOP + ROW * len(report.results) + BOTTOM
    title = f"@{report.login}'s GitHub achievements"
    desc = "; ".join(f"{r.achievement.name}: {value_text(r)}" for r in report.results)
    style = (f"text{{font-family:{FONT}}}"
             f".h{{font-size:17px;font-weight:600;fill:{c['text']}}}"
             f".n{{font-size:13px;font-weight:600;fill:{c['text']}}}"
             f".v{{font-size:12px;fill:{c['muted']}}}"
             f".p{{font-size:10px;font-weight:700}}"
             f".f{{font-size:10px;fill:{c['muted']}}}")
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="card-title card-desc">',
        f'<title id="card-title">{escape(title)}</title>',
        f'<desc id="card-desc">{escape(desc)}</desc>',
        f"<style>{style}</style>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="6" '
        f'fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'<text class="h" x="24" y="36">{escape(title)}</text>',
        '<text class="f" x="24" y="54">Estimated progress toward the next tier</text>',
    ]
    for index, result in enumerate(report.results):
        out.extend(_row(result, TOP + index * ROW, c))
    out.append(f'<text class="f" x="24" y="{height - 14}">Tiers are community-documented, '
               "not official · github-achievements-progress</text>")
    out.append("</svg>")
    # ASCII-only output (non-ASCII becomes &#NNN;) renders the same under any encoding.
    return ("\n".join(out) + "\n").encode("ascii", "xmlcharrefreplace").decode("ascii")
