"""Command-line interface: ``gh-achievements progress | why | card``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable, Dict, List, Optional, Sequence

from . import __version__
from .card import render_card
from .client import GitHubClient, GitHubError, RateLimitError, Transport
from .collect import LOGIN_RE, Collector, Report, collect
from .diagnose import diagnose, render_diagnosis
from .progress import bar
from .tiers import ACHIEVEMENTS, DELAY_NOTE, RETIRED, find_achievement

ISSUES_URL = "https://github.com/Shahnawaz75/github-achievements-progress/issues"
EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_RATE_LIMIT = 0, 1, 2, 3


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-token", action="store_true",
                        help="ignore GITHUB_TOKEN/GH_TOKEN and send anonymous requests (public data only)")
    common.add_argument("--show-private", action="store_true",
                        help="show names of private repositories in the output (hidden by default)")
    common.add_argument("--max-commits", type=int, default=30, metavar="N",
                        help="co-authored commits to map to pull requests (default: 30)")
    common.add_argument("--debug", action="store_true", help="show a traceback on unexpected errors")

    parser = argparse.ArgumentParser(
        prog="gh-achievements",
        description="See how close you are to every GitHub achievement tier, and why a badge "
                    "didn't unlock. Read-only: it never writes to GitHub.",
        epilog="Token: set GITHUB_TOKEN (or GH_TOKEN) for full results. "
               "Exit codes: 0 ok, 1 GitHub or network error, 2 usage error, 3 rate limited.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    progress = sub.add_parser("progress", parents=[common], help="show progress toward every achievement")
    progress.add_argument("username")
    progress.add_argument("--json", action="store_true", help="print JSON instead of text")

    why = sub.add_parser("why", parents=[common], help="explain why an achievement did or didn't unlock")
    why.add_argument("username")
    why.add_argument("achievement", help=", ".join(a.slug for a in ACHIEVEMENTS))
    why.add_argument("--json", action="store_true", help="print JSON instead of text")

    card = sub.add_parser("card", parents=[common], help="write an SVG progress card for a profile README")
    card.add_argument("username")
    card.add_argument("-o", "--output", default="achievements.svg", help="SVG file to write")
    card.add_argument("--theme", choices=("light", "dark"), default="light")
    card.add_argument("--dark-output", metavar="FILE", help="also write a dark-theme card to FILE")
    return parser


def _can_encode(text: str) -> bool:
    try:
        text.encode(getattr(sys.stdout, "encoding", None) or "ascii")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def render_progress(report: Report, ascii_only: bool = False) -> str:
    """Plain-text progress table."""
    lines = [f"GitHub achievements progress for @{report.login} (estimated)", ""]
    if report.notes:
        lines += [f"Note: {note}" for note in report.notes] + [""]
    indent = " " * 28
    for result in report.results:
        ach, st = result.achievement, result.status
        if st is None:
            lines.append(f"  {ach.name:<19}  {'?':<4} {result.reason}")
            continue
        mark = "~" if result.approximate else ""
        if ach.tiered:
            label = st.label + (mark if st.tier else "")
            amount = f"{st.count} {ach.units(st.count)}" if st.maxed else f"{st.count}/{st.next_threshold} {ach.unit}"
            nxt = "top tier" if st.maxed else f"{st.remaining} more for {st.next_label}"
        else:
            label = ("yes" + mark) if st.tier else "-"
            amount = f"{st.count} {ach.units(st.count)}"
            nxt = "likely earned" if st.tier else "none found"
        lines.append(f"  {ach.name:<19}  {label:<4} {bar(st.ratio, 16, ascii_only)} {amount} ({nxt})")
        if result.detail:
            lines.append(indent + result.detail)
    lines += [
        "",
        "~ approximate: based on a scan of recent activity, so the real number can be higher.",
        "Tiers are community-documented, not official. " + DELAY_NOTE,
        "No longer earnable: " + ", ".join(ach.name for ach in RETIRED) + ".",
    ]
    if report.rate:
        budget = ", ".join(f"{name} {v['remaining']:,}/{v['limit']:,}" for name, v in report.rate.items())
        lines.append(f"API budget left: {budget}.")
    lines.append(f"Why didn't a badge unlock? Run: gh-achievements why {report.login} <achievement>")
    return "\n".join(lines)


def _collector(args: argparse.Namespace, client: GitHubClient) -> Collector:
    return Collector(client, args.username, max_commits=max(args.max_commits, 0))


def cmd_progress(args: argparse.Namespace, client: GitHubClient) -> int:
    report = collect(_collector(args, client))
    if args.json:
        print(json.dumps(report.to_dict(args.show_private), indent=2))
    else:
        print(render_progress(report, ascii_only=not _can_encode("█░")))
    return EXIT_RATE_LIMIT if report.rate_limited else EXIT_OK


def cmd_why(args: argparse.Namespace, client: GitHubClient) -> int:
    ach = find_achievement(args.achievement)
    if ach is None:
        _error(f"unknown achievement '{args.achievement}'. Use one of: "
               + ", ".join(a.slug for a in ACHIEVEMENTS + RETIRED))
        return EXIT_USAGE
    collector = _collector(args, client) if ach.earnable else None
    result = diagnose(args.username, ach, collector)
    if args.json:
        print(json.dumps(result.to_dict(args.show_private), indent=2))
    else:
        print(render_diagnosis(result, args.show_private))
    return EXIT_RATE_LIMIT if result.result.reason.startswith("rate limited") else EXIT_OK


def cmd_card(args: argparse.Namespace, client: GitHubClient) -> int:
    report = collect(_collector(args, client))
    if report.rate_limited:
        _error("not writing the card: some checks hit the rate limit, so it would be incomplete")
        for result in report.results:
            if result.reason.startswith("rate limited"):
                _error(f"  {result.achievement.name}: {result.reason}")
        return EXIT_RATE_LIMIT
    targets = [(args.output, args.theme)] + ([(args.dark_output, "dark")] if args.dark_output else [])
    for path, theme in targets:
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(render_card(report, theme))
        except OSError as err:
            _error(f"could not write {path}: {err.strerror or err}")
            return EXIT_ERROR
        print(f"Wrote {path} ({theme} theme) for @{report.login}.")
    return EXIT_OK


COMMANDS: Dict[str, Callable[[argparse.Namespace, GitHubClient], int]] = {
    "progress": cmd_progress, "why": cmd_why, "card": cmd_card,
}


def _error(message: str) -> None:
    print(f"gh-achievements: {message}", file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None, *, transport: Optional[Transport] = None) -> int:
    """Run the CLI and return the exit code."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if not LOGIN_RE.match(args.username):
        _error(f"'{args.username}' is not a valid GitHub username")
        return EXIT_USAGE
    token = None if args.no_token else (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    client = GitHubClient(token or None, transport=transport, on_wait=_error)
    try:
        return COMMANDS[args.command](args, client)
    except RateLimitError as err:
        _error(str(err))
        return EXIT_RATE_LIMIT
    except GitHubError as err:
        _error(str(err))
        return EXIT_ERROR
    except KeyboardInterrupt:
        _error("interrupted")
        return 130
    except BrokenPipeError:  # output piped into e.g. `head`, which closed early
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return EXIT_OK
    except Exception as err:  # last line of defence: never show a raw traceback
        if args.debug:
            raise
        _error(f"unexpected error: {err!r}. Run again with --debug and report it at {ISSUES_URL}")
        return EXIT_ERROR


def run() -> None:
    """Console-script entry point."""
    sys.exit(main())


__all__: List[str] = ["build_parser", "main", "render_progress", "run"]
