---
name: pr-revive
description: Revives a stale pull request and decides whether it still belongs. Reads the PR's intent, checks what changed on the base since it branched (replacements, moved code, new rules), and gives one verdict, REBASE (rebase, test, push), REWRITE (the goal holds but the code is stale) or CLOSE (superseded or no longer worth it, closed only with the user's OK), with evidence. Rebases with range-diff checks and a lease-protected push. Never merges or closes. Use when the user says pr-revive, revive, rebase or update an old PR, bring this branch up to date, or asks whether a stale PR still makes sense.
---

# pr-revive

Bring back the idea, not just the branch. A clean rebase doesn't prove a
PR still belongs in the product.

## Guardrails

- Fetch first: the PR's head, its base, and any branch related to the work.
- Existing changes in the working tree belong to the user. If the tree is dirty or busy with other
  work, use a disposable worktree (`git worktree add`).
- A pr-revive request allows rebasing and updating the PR's branch. It doesn't allow merging, closing,
  changing the base branch, or widening the scope.
- Push a rebased branch only with `--force-with-lease=<branch>:<head sha you recorded>`. Never a
  bare `--force`.
- Don't post a PR comment unless the user asked for one.

## 1. Pin down the intent

Record the PR's URL, state, base, head repository and branch, head SHA, author, checks and review
state. Read the title, body, linked issues, commits, review threads and the full diff. Write the
smallest goal the PR was trying to reach before you judge how it reached it.

Record the merge base, so the PR's own changes and the base's later changes can be compared
separately.

## 2. See what changed around it

Read the commits and diffs that landed on the base since the PR branched. Search merged and open PRs
when titles, paths or behaviour suggest a replacement or a competing fix. Look past overlapping
lines:

- Has the same user-facing problem already been solved another way?
- Did APIs, types, schemas, dependencies or module boundaries change under it?
- Do both sides now claim the same behaviour or rule?
- Was the code it changes deleted, moved or deliberately simplified?
- Would landing it bring back old behaviour, or create two ways to do one thing?
- Is the original benefit still worth the upkeep?

No conflicts in Git doesn't mean current.

## 3. Pick a verdict before pushing anything

| Verdict | When | Then |
| --- | --- | --- |
| REBASE | the goal still matters and the implementation is still the right shape | rebase, resolve, test, push |
| REWRITE | the goal still matters, but a mechanical rebase would keep the wrong implementation | describe the smallest believable rewrite and stop, unless the user also asked you to do it |
| CLOSE | superseded, obsolete, pointed the wrong way, or not worth its cost | cite the evidence (the PR or commit that replaced it, the code that moved) and stop. Don't rebase it, and don't close it without the user's say-so |

Be willing to recommend CLOSE. Age isn't evidence, and effort already spent isn't a reason to keep a PR.

## 4. Rebase without losing the point (REBASE)

1. Make a local branch or disposable worktree at the recorded head.
2. Rebase its commits onto the freshly fetched base.
3. Resolve each conflict by the PR's intent and the base's newer rules. A conflict that exposes a
   product or architecture disagreement means stop and reconsider the verdict, not guess.
4. Compare the series before and after with `git range-diff <old-base>..<old-head> <new-base>..HEAD`,
   then read the final diff. Nothing intended should vanish, and nothing already on the base should
   come back.
5. Run the repo's focused checks for the touched area. Separate real failures from ones that already
   fail on the base or come from infrastructure.
6. Push with the lease tied to the recorded head. If the lease fails, someone pushed: fetch and
   reassess, never overwrite.

If the user wants it carried to ready, hand over to the `pr-babysit` skill after the push.

## Report

Lead with **REBASE**, **REWRITE** or **CLOSE** and the reason in one sentence. Then:

- what changed on the base that matters,
- conceptual conflicts, or that there were none,
- the rebase and push result, if you did them,
- checks run and their results,
- what's left to decide, with the PR link.

Keep what you observed apart from what you judge, and say what you couldn't verify.
