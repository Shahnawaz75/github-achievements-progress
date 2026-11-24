# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-24

First release.

### Added

- `gh-achievements progress <user>`: the estimated tier, next tier, how many more are needed, and a text progress bar for Pull Shark, Pair Extraordinaire, Galaxy Brain, Starstruck, Quickdraw, YOLO and Public Sponsor. Retired badges are listed as no longer earnable.
- `gh-achievements why <user> <achievement>`: a plain-language diagnosis. For Pair Extraordinaire it checks every `Co-authored-by:` trailer and says whether its email is linked to a GitHub account, and it lists commits you authored whose co-authors get the credit.
- `gh-achievements card <user>`: a self-contained SVG card for a profile README, in light and dark themes (`--theme`, `--dark-output`).
- `--json` output for `progress` and `why`.
- A composite GitHub Action (`action.yml`) that regenerates the card on a schedule and commits it only when it changed.
- Works without a token on public data, and says what needs a token.
- Rate-limit handling: shows the remaining budget, waits for short resets, and otherwise stops with a clear message (exit code 3).
- Private repository names are hidden in the output unless `--show-private` is passed.
- Tier thresholds in one data file, `src/github_achievements_progress/tiers.py` (community-documented, not official).
- Documentation: an achievements guide, a GitHub Action guide, and real example output.

[0.1.0]: https://github.com/Shahnawaz75/github-achievements-progress/releases/tag/v0.1.0
