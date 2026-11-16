---
name: pr-ready
description: Takes a change all the way to a pull request that's ready to merge, with nobody watching. Finishes the change on a branch, proves it with evidence observed in the session, gets a second model's review, files a short PR that leads with the problem, looks after CI and review bots until the PR is ready, and stops there for the user to merge. Asking for pr-ready is permission to run the builds, tests and device checks the proof needs. Use only when the user says pr-ready or ready PR, or plainly asks for an unattended run to a ready PR. For a run that also merges, use pr-merge.
---

# pr-ready

Take a change from where it is to a pull request that's ready to merge, then stop. The user merges.

The user asked for this because they aren't watching. Your updates and your final message
won't be read until long after you stop. You own the work from where it is now to a PR that is ready
to merge, and you stop there.

If the user didn't clearly ask for this, don't assume this much autonomy.

## What it grants

For this task only:

- Create a branch, commit, push it, and open a PR.
- Rebase the PR's own branch and push it with `--force-with-lease`.
- Run the builds, tests, simulators, devices, app launches and screenshots the proof needs, without
  asking first. This replaces "ask before building" or "leave testing to me" rules in `AGENTS.md`
  or `CLAUDE.md` for this task.

Rules about *how* to test still apply: the device the project names, one Gradle build at a time,
the project's test command, no `clean`. The grant removes the asking step, nothing else. It doesn't
cover merging, closing PRs, force-pushing other branches, production systems, deleting data, or
anything outside the repo. It doesn't bypass a harness approval prompt either.

## Steps

1. **Finish the change.** Do what the user asked with the smallest change that works. Fix the case
   that happened, not every case that could. If you're on the default branch, branch first.
2. **Prove it.** Evidence for every change in the diff. See Proof.
3. **Get a second read.** Use the `cross-model-review` skill if installed. Otherwise give a fresh subagent the
   diff and the intent (not your conclusions) and ask for bugs only. Fix real findings, decline the
   rest with a reason.
4. **Commit** in the repo's style: look at `git log` and any commit rules in the project's docs. One
   commit per logical change. No AI co-author or "generated with" trailers unless the repo asks for
   them.
5. **File the PR.** See Filing.
6. **Look after it** with the `pr-babysit` skill until it's ready: CI, review bots, reviewers, the
   base branch. Prove each fix before pushing it.
7. **Hand off** at the readiness gate with the report below.

Stay active from step 1 to step 7. If you end your turn while checks or bots are pending, the work
stops, because nobody will prompt you again. Wait with pr-babysit's watcher so an event wakes you.

## Proof

Proof is evidence you observed in this session: command output, a reproduction, a screenshot. Use
the most direct proof the change allows:

- Reproduce the original failure, apply the fix, and watch the same reproduction pass.
- Run the checks CI runs (typecheck, lint, tests) for the touched area.
- Add one focused test that fails without the fix, when the behaviour has none and the repo has a
  test setup.
- For UI and runtime behaviour, run the app and look at the change. Green mocked tests don't prove
  the experience works. Attach screenshots to the PR when they help and you can upload them.

If you can't find a way to prove a change, you don't have full confidence. Ask (see Asking).

## Filing

- Check whether a PR already exists for the branch (`gh pr view`). Update it instead of opening a
  second one.
- Rebase onto the latest default branch first, and read the final diff against it. It should match
  the goal and nothing else.
- Title: the repo's convention (titles often become merge commits). Say why it matters, not which
  mechanism changed: "Stop signing people out on flaky networks", not "Handle 5xx in AuthInterceptor".
- Description: the problem in one or two plain sentences from the user's point of view, then the fix
  in a sentence or two, then one line on how you proved it. No inventory of every file touched. If
  the `unslop` skill is installed, follow its PR genre rules.
- Before submitting, check the title, body, quotes and screenshots for secrets and private details.
- Open a real PR, not a draft, so review bots run. If `gh pr create` hits the GraphQL rate limit,
  use REST: `gh api repos/<owner>/<repo>/pulls -f title=... -f head=... -f base=... -F body=@<file>`.

## Readiness gate

Ready means all of these hold on the latest head:

- Your proof covers every change in the diff, including fixes made during review.
- Required checks are green.
- Review bots have finished, and every finding is fixed or answered with a reason.
- No human review is requesting changes.
- The branch is up to date with its base and GitHub reports it mergeable.

Before handing off, fetch and recheck the live PR: open, not a draft, not set to auto-merge. Disable
auto-merge and leave any merge queue if either is on, and say so. Never merge, enable auto-merge,
enter a merge queue or push to the default branch.

## Asking

A question in a normal message goes unseen, and the thread looks finished. Ask with the harness's
question tool so the thread shows it's waiting (`AskUserQuestion` in Claude Code,
`request_user_input` in Codex). Put everything in the question: the PR link, what blocks you, the
options with your recommendation first.

Ask only when you can't go on alone:

- You can't prove the change.
- The gate can't pass and you can't fix that yourself.
- The next step is outside the grant.
- The goal is ambiguous in a way that changes the result.
- Another PR makes this one obsolete.

Decide everything else yourself with sensible defaults and list those decisions in the report. If
there's no question tool or no answer comes, take the safe path: leave the PR as it is and start
your final message with the question.

## Report

Lead with the verdict: **Ready to merge** (the gate passed), **Waiting on a human review**
(confirm that's the only blocker), or **Blocked** (what blocks it, what you tried, what's needed).
Then:

- the PR link and final head,
- how you proved it,
- what the reviewer and the bots found, and what you did about each,
- decisions you made on the user's behalf,
- remaining risks or follow-ups,
- that the PR is open and unmerged.
