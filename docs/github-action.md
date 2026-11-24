---
title: "GitHub Action: a daily GitHub achievements progress card for your profile README"
description: "Add a self-updating SVG card with your GitHub achievement tiers and progress to your profile README using the github-achievements-progress GitHub Action."
permalink: /github-action/
---

# GitHub Action: keep an achievements progress card in your profile README

The action installs `gh-achievements`, draws the SVG card from your current GitHub data, and commits it to the repository only when it changed. Put it in your **profile repository** (the public repository named exactly like your username) and the card in your profile README stays up to date.

## Quick setup

1. In your profile repository, create `.github/workflows/achievements.yml`:

   ```yaml
   name: Update achievements card

   on:
     schedule:
       - cron: "17 4 * * *"   # every day at 04:17 UTC
     workflow_dispatch:        # lets you run it by hand from the Actions tab

   permissions:
     contents: write           # needed to commit the card

   jobs:
     card:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v7
         - uses: Shahnawaz75/github-achievements-progress@main   # pin a release tag or commit SHA once available
           with:
             output: achievements.svg
             dark-output: achievements-dark.svg
             # token: ${{ secrets.ACHIEVEMENTS_TOKEN }}   # optional, see "Which token?"
   ```

2. Run it once from the **Actions** tab (**Run workflow**), so the SVG files exist.
3. Add the card to your profile `README.md`:

   ```html
   <picture>
     <source media="(prefers-color-scheme: dark)" srcset="achievements-dark.svg">
     <img alt="My GitHub achievements progress" src="achievements.svg">
   </picture>
   ```

## Inputs

| Input | Default | Description |
|---|---|---|
| `username` | repository owner | GitHub username to report on. |
| `output` | `achievements.svg` | Path of the SVG card to write. |
| `theme` | `light` | Theme of the card in `output`: `light` or `dark`. |
| `dark-output` | empty | Optional path of a second, dark-theme card. |
| `token` | `${{ github.token }}` | Token for the read-only API calls. See below. |
| `commit` | `true` | Commit and push the card(s) when they changed. Set to `false` to commit yourself. |
| `commit-message` | `chore: update GitHub achievements card` | Message of that commit. |
| `python-version` | `3.12` | Python version used to run the tool. |

Output: `changed` is `"true"` when a card changed and was committed.

## Which token?

The token is only used to **read** data. Pushing the commit uses the credentials from `actions/checkout`, which is why the workflow needs `permissions: contents: write`.

- **Default (`github.token`)**: works with no setup. It's limited to the repository running the workflow plus public data, so the card counts your **public** activity only. Some GraphQL fields may not be available to this kind of token; those rows then show "not available" on the card.
- **Personal access token (recommended if you work in private repositories)**: GitHub's own counts seem to include private contributions (see the [FAQ](achievements.md#do-private-contributions-count)), so a token that can read your private repositories gives numbers closer to what GitHub uses. Create a **fine-grained** token with **read-only** access:
  1. Go to **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**.
  2. Resource owner: you. Repository access: **All repositories**.
  3. Repository permissions, all **Read-only**: **Contents**, **Pull requests**, **Discussions** (Metadata is added automatically).
  4. In your profile repository, add it as a secret named `ACHIEVEMENTS_TOKEN` (**Settings > Secrets and variables > Actions**) and pass `token: ${{ secrets.ACHIEVEMENTS_TOKEN }}`.

  A classic token with the `repo` scope also works, but it can write to all your repositories, which is more than this needs.

Your private data stays private: the card shows only counts and tiers, never repository names, and the token is never printed in the logs.

## Troubleshooting

- **`Permission to <repo> denied to github-actions[bot]` when pushing.** Add `permissions: contents: write` to the workflow, or allow **Read and write permissions** under **Settings > Actions > General > Workflow permissions**.
- **A row says "not available" or "needs a token".** The token can't read that data. Use a personal access token as described above.
- **The job failed with exit code 3.** GitHub's rate limit was hit. The card is not changed when data is incomplete, and the next scheduled run will try again.
- **The schedule stopped running.** GitHub disables scheduled workflows in public repositories after 60 days without repository activity. Re-enable it from the Actions tab, or run it by hand now and then.
- **The card looks out of date.** GitHub caches README images for a short time. The card in the repository is the source of truth.

## Without the action

The action is a thin wrapper around the CLI. You can do the same in any CI system:

```bash
pip install git+https://github.com/Shahnawaz75/github-achievements-progress
GITHUB_TOKEN=... gh-achievements card <username> -o achievements.svg --dark-output achievements-dark.svg
```
