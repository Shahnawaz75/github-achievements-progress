---
title: "GitHub achievements guide: every badge, its tiers, and why it doesn't unlock"
description: "How to earn every GitHub achievement (Pull Shark, Pair Extraordinaire, Galaxy Brain, Starstruck, Quickdraw, YOLO, Public Sponsor), the x2, x3 and x4 tier thresholds, and the common reasons a badge doesn't unlock."
permalink: /achievements/
---

# GitHub achievements guide: every badge, its tiers, and why it doesn't unlock

GitHub achievements are the small badges in the **Achievements** section of your profile. GitHub introduced them in 2021 and expanded them in June 2022. Some badges have tiers: after the first badge, GitHub adds a label **x2** (bronze), **x3** (silver) or **x4** (gold) as you reach higher counts.

GitHub doesn't publish the exact rules. The thresholds below are **community-documented**: people compared their activity with their badges (see [Schweinepriester/github-profile-achievements](https://github.com/Schweinepriester/github-profile-achievements) and [drknzz/GitHub-Achievements](https://github.com/drknzz/GitHub-Achievements)). They have been stable for a long time, but GitHub can change them at any time.

> **Check your own numbers:** `gh-achievements progress <username>` shows your count, estimated tier and how many more you need for every achievement below. `gh-achievements why <username> <achievement>` explains a badge that didn't unlock. See the [README](https://github.com/Shahnawaz75/github-achievements-progress#readme).

## Contents

- [All achievements at a glance](#all-achievements-at-a-glance)
- [Pull Shark](#pull-shark)
- [Pair Extraordinaire](#pair-extraordinaire)
- [Galaxy Brain](#galaxy-brain)
- [Starstruck](#starstruck)
- [Quickdraw](#quickdraw)
- [YOLO](#yolo)
- [Public Sponsor](#public-sponsor)
- [Retired achievements](#retired-achievements)
- [Other badges you may see](#other-badges-you-may-see)
- [How long do achievements take to show up?](#how-long-do-achievements-take-to-show-up)
- [Do private contributions count?](#do-private-contributions-count)
- [How to hide achievements](#how-to-hide-achievements)
- [Please don't farm badges](#please-dont-farm-badges)

## All achievements at a glance

| Achievement | How to earn it | Default | x2 (Bronze) | x3 (Silver) | x4 (Gold) |
|---|---|---|---|---|---|
| [Pull Shark](#pull-shark) | Pull requests you opened that were merged | 2 | 16 | 128 | 1024 |
| [Pair Extraordinaire](#pair-extraordinaire) | Co-authored commits in merged pull requests | 1 | 10 | 24 | 48 |
| [Galaxy Brain](#galaxy-brain) | Answers accepted in Q&A discussions | 2 | 8 | 16 | 32 |
| [Starstruck](#starstruck) | Stars on one repository you own | 16 | 128 | 512 | 4096 |
| [Quickdraw](#quickdraw) | Close an issue or PR within 5 minutes of opening it | 1 | - | - | - |
| [YOLO](#yolo) | Merge your own PR without a code review | 1 | - | - | - |
| [Public Sponsor](#public-sponsor) | Sponsor someone through GitHub Sponsors | 1 | - | - | - |
| [Arctic Code Vault Contributor](#retired-achievements) | 2020 GitHub Archive Program | no longer earnable | | | |
| [Mars 2020 Contributor](#retired-achievements) | Mars 2020 Helicopter Mission | no longer earnable | | | |

## Pull Shark

**How to earn it:** open pull requests that get **merged**.

| Tier | Merged pull requests |
|---|---|
| Default | 2 |
| x2 (Bronze) | 16 |
| x3 (Silver) | 128 |
| x4 (Gold) | 1024 |

**What counts:** pull requests that **you opened** and that someone (you or a maintainer) merged. The repository can be yours or someone else's.

**Common reasons it doesn't unlock or level up:**

- **The PR was closed, not merged.** Closed-without-merge and still-open PRs don't count. `gh-achievements why <you> pull-shark` shows merged, closed and open separately.
- **You're counting PRs you reviewed or merged for others.** Only PRs you authored count toward your Pull Shark.
- **It hasn't shown up yet.** New tiers can take hours to a few days.

## Pair Extraordinaire

**How to earn it:** be named as a **co-author** on a commit in a **merged** pull request.

| Tier | Co-authored merged pull requests |
|---|---|
| Default | 1 |
| x2 (Bronze) | 10 |
| x3 (Silver) | 24 |
| x4 (Gold) | 48 |

Co-authors are added with a trailer at the end of the commit message, after a blank line ([GitHub Docs: creating a commit with multiple authors](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors)):

```text
Add the export command

Co-authored-by: Ada Lovelace <12345+ada@users.noreply.github.com>
```

**Who gets the badge:** the people named in `Co-authored-by:`. The PR author doesn't earn Pair Extraordinaire from their own PR just by adding co-authors. This is the most common surprise.

**Which email to use:** the email must be one that is **linked to the co-author's GitHub account**. The safest choice is their noreply address, `<id>+<username>@users.noreply.github.com`. You can find your own on the [email settings page](https://github.com/settings/emails) when "Keep my email addresses private" is on, or build it from your numeric id at `https://api.github.com/users/<username>`.

**Common reasons it doesn't unlock:**

1. **You were the PR author.** Your co-authors get the credit, not you. `gh-achievements why <you> pair` lists commits you authored with co-authors, so you can see where your credit went.
2. **The email isn't linked to an account.** If the email in the trailer doesn't belong to any GitHub account (a typo, an old work address, an unverified email), GitHub cannot credit anyone. The tool checks every trailer and tells you *"this email is not linked to any GitHub account, so GitHub cannot credit it"*.
3. **The pull request wasn't merged.** Commits pushed straight to a branch, or in PRs that were closed without merging, don't count.
4. **The trailer was lost on merge.** When a PR is squash-merged, the final commit message is what counts. If someone edits that message and drops the `Co-authored-by:` lines, the credit is gone.
5. **Wrong format or position.** The trailer has to be on its own line in the **last** part of the message, after a blank line, as `Co-authored-by: Name <email>`. Typos like `Co-author:` or a missing `<` `>` break it.
6. **Too early.** Badges can take a few days to appear after the PR is merged.

## Galaxy Brain

**How to earn it:** answer questions in GitHub **Discussions** and get your answer **marked as the answer**.

| Tier | Accepted answers |
|---|---|
| Default | 2 |
| x2 (Bronze) | 8 |
| x3 (Silver) | 16 |
| x4 (Gold) | 32 |

**What counts:** a discussion comment that the person who asked, or a maintainer, marked with **Mark as answer**. That's only possible in categories that accept answers, usually called **Q&A**.

**Common reasons it doesn't unlock:**

- **The answer wasn't marked.** Upvotes, thanks and "this worked!" replies don't count. Only the accepted answer does.
- **The discussion is in a category without answers** (for example "General" or "Ideas").
- **It's in GitHub's own Community discussions.** GitHub [turned off achievements in github.com/orgs/community](https://github.com/orgs/community/discussions/106536) on 2024-02-06 because of spam. Answers there no longer count, and `gh-achievements` leaves them out.
- **You have 1 answer.** The first badge needs 2.

## Starstruck

**How to earn it:** own a repository that many people star.

| Tier | Stars on one repository |
|---|---|
| Default | 16 |
| x2 (Bronze) | 128 |
| x3 (Silver) | 512 |
| x4 (Gold) | 4096 |

**What counts:** the stars on a **single** repository. It isn't the sum of stars across all your repositories. `gh-achievements` checks the non-fork repositories owned by your personal account.

**Common reasons it doesn't unlock:**

- **You're adding up stars across repositories.** 300 stars spread over 20 repos is not 300 stars on one repo.
- **The repository isn't owned by your personal account.** Community reports about repositories in organizations vary.
- **Too early.** The badge can take a while after the star count crosses the threshold.

## Quickdraw

**How to earn it:** close an issue or pull request **within 5 minutes** of opening it. One tier.

**What counts:** an issue or PR that was closed within 5 minutes. Community reports say a PR merged within 5 minutes counts too, since merging closes it.

**Common reasons it doesn't unlock:**

- **It took longer than 5 minutes** from opening to closing. The clock starts when the issue or PR is created, not when you start working on it.
- **Too early.** Give it some time.

`gh-achievements why <you> quickdraw` lists recent issues and PRs that were closed within 5 minutes, with the exact time it took.

## YOLO

**How to earn it:** **merge your own pull request without a code review.** One tier.

**Common reasons it doesn't unlock:**

- **The PR had a review.** An approval, a "request changes" or even a review comment means it was reviewed.
- **Someone else merged it.** You have to merge your own PR.
- **Branch protection requires reviews** in that repository, so the merge needed a review anyway.

`gh-achievements why <you> yolo` lists your recent PRs that you merged yourself with zero reviews.

## Public Sponsor

**How to earn it:** sponsor a developer or organization through [GitHub Sponsors](https://github.com/sponsors). One tier.

**Notes:**

- Both monthly and one-time sponsorships are reported to work.
- Other people can't see private sponsorships, and past one-time sponsorships may not show in the API, so a tool (including this one) can show `0` even if you once sponsored someone.

## Retired achievements

These were awarded once and **can no longer be earned**:

- **Arctic Code Vault Contributor:** for code in repositories that were part of the [2020 GitHub Archive Program](https://archiveprogram.github.com/) snapshot.
- **Mars 2020 Contributor:** for code in repositories used by the Mars 2020 Helicopter Mission (Ingenuity). GitHub Docs keep the list of qualifying repositories.

## Other badges you may see

- **Highlights** such as **PRO**, **Developer Program Member**, **Security Bug Bounty Hunter**, **GitHub Campus Expert** or **GitHub Star** appear on profiles too. They are profile highlights for programs and plans, not achievements, so there's no progress to track.
- **Heart On Your Sleeve** (react with a heart) and **Open Sourcerer** (PRs merged in several public repositories) have been reported as **in testing** and not generally available.
- **Finishing Touch** is reported for merged pull requests that improved GitHub's own UI quality. It isn't something this tool can track.

## How long do achievements take to show up?

Often a few hours, but **one to several days** is common in community reports. If `gh-achievements` says you qualified only recently, wait a few days before assuming something is wrong. If a week has passed, run `gh-achievements why <you> <achievement>` to look for one of the problems above.

## Do private contributions count?

GitHub doesn't document this. In our own test account, the **public** merged-PR count (14) was below the Pull Shark x2 threshold (16), while the profile showed **x2**; with a token that can read private repositories, the count was 18. That suggests private merged PRs count, but treat it as an observation, not a rule.

To include private activity in `gh-achievements`, use a token that can read your private repositories (for example `gh auth token`, or a personal access token in the GitHub Action). The tool hides private repository names in its output unless you pass `--show-private`.

## How to hide achievements

According to [GitHub Docs](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/managing-contribution-settings-on-your-profile/showing-your-private-contributions-and-achievements-on-your-profile):

- **All achievements:** open **Settings**, and under **Profile settings** deselect **Show Achievements on my profile**, then click **Update preferences**.
- **A single achievement:** open your profile, click the badge in the **Achievements** section, then click the eye icon (**Hide from profile**). Hidden badges stay visible to you.

## Please don't farm badges

Badges are fun because they reflect real work. Creating throwaway issues, empty pull requests or fake co-authors only to unlock them adds noise for maintainers, and GitHub has [warned](https://github.com/orgs/community/discussions/106536) that spam created to earn achievements can lead to content removal or account restrictions. `gh-achievements` only reads and explains your data; it never creates activity.

---

Found a threshold that changed, or a reason we missed? [Open an issue](https://github.com/Shahnawaz75/github-achievements-progress/issues/new/choose).
