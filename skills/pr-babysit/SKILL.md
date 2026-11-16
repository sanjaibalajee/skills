---
name: pr-babysit
description: Looks after an open pull request until it's ready. Watches CI and review bots with a bundled watcher that wakes the agent once per real event, checks each finding against the code, fixes the real ones, answers the false ones with a reason, reruns flaky jobs once, keeps the branch current with its base, and stops when the PR is ready for a human. Use when the user says pr-babysit, babysit, watch or mind this PR, get it green, or deal with the review bots. Merges only when told to.
---

# pr-babysit

Keep a PR moving while nobody watches it: CI, review bots, reviewers and the base branch. Fix what
breaks, answer what's wrong, keep the PR at its original size, and leave the merge to a human.

`<skill-dir>` below is the folder holding this file. Claude Code exposes it as `${CLAUDE_SKILL_DIR}`.

Needs an authenticated `gh` and `python3`.

## Start

1. Find the PR: the number or URL the user gave, else `gh pr view --json number,url,headRefName`
   for the current branch. Note the base branch and how the repo merges (recent merged PRs).
2. Handle what's already there before waiting: failed checks, unanswered review comments, a stale
   branch.
3. Start the watcher. One watcher per PR, never your own `sleep` loop.

## The watcher

```bash
python3 <skill-dir>/scripts/pr_watch.py <pr-number-or-url> [--until ready|green|any]
```

It prints one line per event and exits on its own:

| Exit | Means | Do |
| --- | --- | --- |
| 0 | `--until` met, or merged | check readiness yourself, then hand off |
| 1 | needs action: check failed, conflict, behind, unresolved threads, closed | act, push, start it again |
| 2 | bad input, or another watcher already has this PR | read stderr; don't start a second one |
| 3 | timed out with nothing to do (55 min by default) | start it again |

- `ready` (the default): required checks green, not behind, no unresolved review threads, and each
  review bot that reviewed this PR before has reviewed the latest push (or 15 minutes passed).
- `green`: required checks only, for repos without review bots.
- `any`: wake on the first event.

In Claude Code, run it under the **Monitor** tool with an hour's timeout so each line wakes you.
Without a monitor, run it as one blocking command with a long timeout. Start it again after every
push, after you handle an exit 1, and after a resume. It remembers what it already reported.

When an event needs nothing from you, go back to waiting without a message. Never post or say "still
waiting".

## Handling events

Only act on checks and comments newer than the latest push.

**A failed check.** Read the log (`gh run view <run-id> --log-failed`). Decide whether the failure
is the change's fault or the infrastructure's:

- Yours: fix it, prove the fix locally where you can, push.
- A flake (network timeout, runner died, a test that fails on main too): rerun once with
  `gh run rerun <run-id> --failed`. A second failure is real until shown otherwise. Say which it was.

**A review comment or bot finding.** Check it against the source before touching code. Bots are
useful and often wrong.

- Real and in scope: the smallest fix. Prefer the fix that deletes or narrows code.
- Real but out of scope: reply that it's a follow-up and list it in your report.
- Wrong: reply with the reason and the evidence (file:line, a test, output), then resolve the thread.
- Never resolve a human reviewer's thread you disagreed with. Reply and leave it for them.

Replies are short: the conclusion, then the evidence. No thanks-for-the-review filler. Follow the
repo's or user's rule on marking agent-written comments.

**Advisory bots** (CodeRabbit and others the repo treats as optional): treat their findings like any
other, but never hold the PR for them.

**Behind or conflicting.** Fetch, rebase onto the base, resolve conflicts by the PR's intent and the
base's newer rules, rerun the focused checks, push with
`git push --force-with-lease=<branch>:<sha you last saw>`. Never a bare `--force`.

## Keep it the size it was

Review loops grow PRs one cheap-looking fix at a time. Fix real bugs in the case the PR is for.
Decline the rest with a one-line reason and list them as follow-ups: tests nobody needs, guards for
cases that can't happen, extra compatibility, tiny performance wins. If the diff grew, cut before you
push.

## Stop

Stop when the watcher exits 0 and you've confirmed on the latest head:

- every change since the last proof is proven,
- required checks are green,
- review bots have finished and each finding is fixed or answered,
- no human review is requesting changes,
- the branch is current with its base and GitHub says it's mergeable.

Then report: the PR link, the final head, what you fixed, what you declined and why, flakes you
rerun, and anything left for a human.

**Never merge** unless the user asked for it in this task (or invoked `pr-merge`). Never use
`--admin` or bypass branch protection.

If another PR makes this one obsolete, stop watching and tell the user. Close it only if they said
so.

## Rate limits

`gh pr view` and `gh pr checks` use GraphQL; the watcher mostly uses REST, which has its own limit.
If GraphQL runs out, read PRs with `gh api repos/<owner>/<repo>/pulls/<n>` and checks with
`gh api repos/<owner>/<repo>/commits/<sha>/check-runs`. Check with
`gh api rate_limit --jq .resources.graphql`, and wait for the reset with one background command
rather than retrying in a loop.
