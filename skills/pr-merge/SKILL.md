---
name: pr-merge
description: Takes a change all the way to a merged pull request with nobody watching. Runs the pr-ready workflow (finish, prove, second-model review, file, look after CI and bots), then merges once the merge gate passes, using the repo's merge method and never bypassing branch protection. Asking for pr-merge is permission to run the checks the proof needs and to merge this one PR. Use only when the user says pr-merge or ship and merge, or plainly asks for an unattended run that ends merged.
---

# pr-merge

Everything `pr-ready` does, then merge once the gate passes. The user asked for this because they
want the change finished and merged without coming back to it.

Read the `pr-ready` skill and follow its steps, proof rules, filing rules, readiness gate and asking
rules. An explicit pr-merge request grants everything pr-ready grants, without a separate request.
The differences are below and win over pr-ready's.

If the user didn't clearly ask for this, don't assume permission to merge.

## The extra grant

Merge this task's PR once the merge gate passes. Nothing else changes: no other PRs, no pushes to
the default branch, no `--admin`, no bypassing branch protection or rulesets.

## Merge gate

pr-ready's readiness gate, plus:

- Right before merging, `git fetch` and check the live PR again. Never merge when it's behind or
  conflicting, or when base commits that landed after the last green run touch this PR's files.
  Rebase, push, wait for green again.
- Merge with the method the repo uses. Check the allowed methods (`gh repo view --json
  mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed`) and how recent PRs were merged.
- If the repo uses a merge queue or auto-merge, use it and stay until GitHub reports the PR merged.
- An automated review asking for "human review" can be set aside when your proof covers the whole
  diff and no human has asked for changes. A human's request for changes cannot.
- If required approvals are missing, you can't merge. Stop at pr-ready's handoff with the
  verdict **Waiting on a human review**.

## After the merge

- Confirm it: `gh pr view <n> --json state,mergeCommit`.
- Delete the remote branch only if the repo does that for merged PRs.
- Stop any PR watcher still running.

## Report

Lead with **Merged** and the merge commit, then pr-ready's report items: the PR link, proof,
review and bot outcomes, decisions made for the user, and follow-ups. If you stopped before merging,
lead with the reason, as pr-ready's report does.
