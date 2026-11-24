# Contributing

Thanks for helping! Bug reports, corrections to the achievement rules, and pull requests are all welcome.

## Ground rules

- **Read-only, always.** The tool only reads GitHub data and explains it. Features that create pull requests, issues, commits, stars, sponsorships or any other activity to "farm" badges will not be accepted.
- **Honest numbers.** Anything that's estimated or community-documented must say so in the output and the docs.
- **Privacy.** Never print, log or commit a token. Private repository names stay hidden unless the user passes `--show-private`. The SVG card shows counts only.
- **Small and dependency-free.** The package uses only the Python standard library. Please discuss before adding a dependency.

## Development setup

```bash
git clone https://github.com/Shahnawaz75/github-achievements-progress
cd github-achievements-progress
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -e ".[test]"
python -m pytest
```

The tests never touch the network: `tests/conftest.py` provides a fake HTTP transport that answers from the JSON files in `tests/fixtures/`. To add a case, add or edit a fixture and a route in `token_routes()`.

To try your change against the real API (read-only):

```bash
export GITHUB_TOKEN=$(gh auth token)   # PowerShell: $env:GITHUB_TOKEN = (gh auth token)
gh-achievements progress <your-username>
```

## Project layout

| Path | What it does |
|---|---|
| `src/github_achievements_progress/tiers.py` | Achievement definitions and tier thresholds (the data file) |
| `src/github_achievements_progress/progress.py` | Tier math and text progress bars |
| `src/github_achievements_progress/client.py` | Read-only REST and GraphQL client, rate limits, errors |
| `src/github_achievements_progress/collect.py` | One calculator per achievement |
| `src/github_achievements_progress/diagnose.py` | The `why` explanations |
| `src/github_achievements_progress/card.py` | The SVG card |
| `src/github_achievements_progress/cli.py` | Command-line interface |
| `action.yml` | The composite GitHub Action |

## How to update tiers when GitHub changes them

GitHub doesn't publish achievement thresholds, so they can change without notice. When they do:

1. **Collect evidence.** For example, your badge turned x2 at a different count, several community reports agree, or GitHub published a changelog or docs page. Link it in the issue or PR (there's a "GitHub changed an achievement" issue template).
2. **Edit the data file.** Change the `thresholds` tuple of the achievement in `src/github_achievements_progress/tiers.py` and update the "Last checked" date and sources in its docstring. To retire a badge, move it to `RETIRED` with `earnable=False`. The tier text in `why` is generated from this file, so you don't need to edit `diagnose.py` for a threshold change.
3. **Update the test** `test_registry_matches_the_documented_tiers` in `tests/test_tiers.py`, then run `python -m pytest`.
4. **Update the tables** in `README.md` ("All GitHub achievements and tiers") and `docs/achievements.md`.
5. **Add a line to `CHANGELOG.md`** under a new version.
6. Optionally regenerate the example cards: `gh-achievements card Shahnawaz75 -o docs/example-card.svg --dark-output docs/example-card-dark.svg`.

## Pull requests

- Keep changes focused, and add or update tests for behavior changes.
- Run `python -m pytest` before opening the PR. CI runs the tests on Ubuntu and Windows with Python 3.9 to 3.13.
- Write user-facing text short and plain. Many users read English as a second language.

## Reporting bugs

Please include the command, the output (without tokens), the version (`gh-achievements --version`) and what your GitHub profile shows. Private repository names are hidden by default; keep them out of public issues.
