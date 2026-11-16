---
name: cross-model-review
description: Has a different model review a change and loops until it runs out of real objections. Runs the Codex CLI read-only as the reviewer when it's installed (else another provider the harness offers, else a fresh subagent), keeps a ledger of findings by severity, fixes the real ones with the smallest change, pushes back on the rest with evidence, and stops after three rounds. Say panel for a panel of reviewers from different providers with scores out of 10. Use when the user says cross-model review, second opinion, cross-check, review with codex, or panel review, or when pr-ready asks for a review.
---

# cross-model-review

Hand the diff to a reviewer that didn't write it and doesn't share your blind spots, then argue it
out. The goal is a correct change at its intended
size. A reviewer's approval at any cost isn't.

## Pick the reviewer

In this order:

1. The Codex CLI (`codex` on `PATH`): a different model family, run read-only.
2. Another provider the harness exposes, such as T3 Code's `delegate_task`, a Gemini CLI, or a
   subagent set up to run another provider's model.
3. A fresh subagent of your own model, given only the brief. Say in the report that it's the same
   model family, so a weaker check.

If the user named a reviewer, use only that one. If it isn't reachable, say so instead of
substituting.

## Budget

- Three rounds. Round 1 reviews the whole change; later rounds only the code that changed and the
  findings still open.
- Up to five only for security, auth, payments, data loss or concurrency, while a blocker or
  should-fix stays open with evidence, or when the user asks.
- Stop early when a round returns only nits. Declined nits and comment or formatting fixes need no
  new round.
- One reviewer per round (panel mode aside). The reviewer never starts its own subagents.

## 1. Scope

- `git status --short`. Don't stash, discard or include unrelated changes. If the change's paths
  don't separate cleanly from other work in the tree, stop and ask.
- Find the base after `git fetch origin`. On a PR: `git merge-base HEAD origin/<base>`. Local work:
  `git merge-base HEAD origin/<default-branch>`. Uncommitted work only: `HEAD`.
- Use one diff command for every round: `git diff <base> -- <paths>`, plus untracked files.
- Write the intent and what's out of scope in two sentences.
- Run the checks that cover the change before round 1. Don't send code that doesn't build. Note
  checks that were already failing on the base.

## 2. The brief

Write it to a scratch file:

```text
Review only. Don't edit files, commit, push, comment on GitHub, or start subagents.
Repo: <absolute path>   Base: <sha>
Intent: <one or two sentences>
Out of scope: <list>
Checks run: <command> -> <result>
See the change with: git diff <base> -- <paths>   Untracked files to read: <list>
Read the surrounding code and the callers. Find bugs, broken callers, and mismatches with the intent.
Skip style unless it hides a bug. Hold the change to its smallest form: flag code, tests or guards
the intent doesn't need.
Severity: blocker = the intended case is wrong. should = a real bug callers will hit, within the
intent. nit = anything else (other paths, rare cases, small performance costs, extra compatibility).
Reply in exactly this shape:
VERDICT: APPROVE or CHANGES
H1 [blocker|should|nit] <file>:<line> <claim>. Fix: <suggestion>
Keep ids stable across rounds.
```

## 3. Run a round

```bash
codex exec -s read-only -C <repo> -o <scratch>/review-round-1.md - < <scratch>/review-brief.md
```

- `-s read-only` stops it from writing; `-o` saves its final message. Pass `-m <model>` only when
  the user named one.
- It can take minutes. Run it in the background and wait for it to finish. Don't poll, and don't
  start a second reviewer.
- Don't edit the files under review while it runs.
- A timeout, an error or an empty reply is not approval. Retry once, then report the blocker.

For the subagent fallback, give it the brief and nothing else: not your reasoning, not your
conclusion.

## 4. Answer the findings

Check each finding and its severity yourself. Another path, a rare case or a small cost is a nit
whatever label it came with.

| Your call | Do |
| --- | --- |
| agree | the smallest fix. Prefer deleting or narrowing code over a new lock, cache, helper or option. Add one focused test that fails without the fix when the intent needs it |
| disagree | say why, with evidence: file:line, a test, command output |
| out of scope, or a nit | decline in one line and list it as a follow-up |

Keep a ledger in a scratch file: id, severity, outcome (`fixed`, `disagree`, `declined`), evidence.
Never agree just to end the loop. After fixing, rerun the checks and `git diff --shortstat <base>`.
If the review grew the diff, cut before the next round.

## 5. The next round

Run one only if budget remains and a blocker or should-fix is open, behaviour code changed, or the
last approval doesn't cover the current diff. Send the round 1 brief, the ledger, the same diff
command, and what changed since last round. Ask the reviewer to mark each old id `resolved` or
`still open: <reason>` and to look only at changed code and open ids.

## 6. Stop

Stop when you agree: APPROVE on the current diff, no blocker or should-fix open, and no concern of
your own.

Stop when you're stuck: an item is still disputed after two replies, or the budget ran out. Show both
sides in two or three lines each and let the user decide. Running out of budget is not approval.

Don't push during the loop. Push afterwards only if the user asked to push, ship or update the PR.

## Report

Rounds run, the reviewer (the model name the tool reports, or "not exposed"), the final verdict,
diff size before and after, each finding with its outcome and reason, follow-ups, and whether you
pushed. Put a review line in a PR description only if the repo's conventions allow naming agent
tools there.

## Panel mode

When the user asks for a panel, run three reviewers from different providers in parallel, for example Codex, a Claude subagent and a Gemini CLI, each with the same brief plus
"Score the change out of 10."

- All read-only. Don't edit while any of them is still reading the checkout.
- Don't wait idle: check each result against the code as it lands, and plan fixes while the others
  run.
- A full pass by all three is one round. Fixes start a fresh round.
- Loop until every reviewer is satisfied or the budget ends, still fighting scope growth.
- If fewer than three providers are reachable, say which ran. Never invent a score; write
  `no score`.

```markdown
| Reviewer | Round 1 | Round 2 |
| --- | --- | --- |
| Codex (model as reported) | 7/10 | 9/10 |
| Claude subagent | 8/10 | 9/10 |
| Gemini | no score | 8/10 |
```
