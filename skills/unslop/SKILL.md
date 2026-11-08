---
name: unslop
description: Rewrite text so it reads like a person wrote it. Strips AI tells (puffery, filler, praise, stacked hedges, em dashes, bold-label bullets, emoji headers, cute closers, AI attribution trailers) while keeping facts, code, numbers and the author's voice. Use when the user says unslop, deslop, "sounds too AI", "make it human", humanize or tighten, or asks to clean up a README, docs page, PR description, commit message, changelog, email, Slack message, blog post, bio or portfolio copy. Also turns a voice-dictated draft into a clean message and audits only the lines a branch added. Ships a stdlib scanner that flags tells by line in Markdown, HTML, commit messages and diffs, and can block sloppy commits as a commit-msg hook.
---

# unslop

Rewrite text so a careful person could have written it. Same facts, same stance, fewer words, no tells.
The target is text a reader trusts. Passing a detector is a side effect.

`<skill-dir>` below is the folder holding this file. Claude Code exposes it as `${CLAUDE_SKILL_DIR}`.

## Pick the mode

| The user gives you | Mode | You |
| --- | --- | --- |
| pasted text, "unslop this" | Rewrite | return the rewrite |
| a file, folder or glob | Files | edit in place, report counts before and after |
| "unslop this branch", "clean my docs changes" | Diff | touch only lines the branch added |
| a commit message, PR body, changelog | Ship | apply the genre rules in `references/genres.md` |
| a voice-dictated draft | Dictation | resolve self-corrections, drop fillers, keep their voice |
| "unslop yourself", "stop sounding like AI" | Session | apply these rules to your own replies from now on |

## Workflow

1. **Read all of it first.** Name the genre, the reader, and the one thing the text must get across.
   Open `references/genres.md` for that genre.
2. **Scan for an inventory.**
   ```bash
   python3 <skill-dir>/scripts/scan.py README.md docs/*.md       # Markdown or text
   python3 <skill-dir>/scripts/scan.py plan.html                  # HTML, visible text only
   pbpaste | python3 <skill-dir>/scripts/scan.py -                # pasted text
   git diff main...HEAD | python3 <skill-dir>/scripts/scan.py --diff -   # only added lines
   python3 <skill-dir>/scripts/scan.py --commit-msg msg.txt       # commit message checks
   python3 <skill-dir>/scripts/scan.py --dictation -              # speech fillers too
   ```
   The scanner catches word and phrase tells. It can't see empty sentences, padding, structure or rhythm.
   Read for those yourself with `references/patterns.md`.
3. **Rewrite in four passes.**
   1. *Cut.* Delete what says nothing: preambles, restated summaries, praise, sign-offs, "it's worth
      noting". If a paragraph can go with no loss, it goes.
   2. *Make it concrete.* Swap each puffed word for the plain word or the actual fact. Name the mechanism
      ("retries the Razorpay capture twice") instead of the feeling ("makes payments smoother").
   3. *Fix the shape.* Headings only where a reader navigates. Bullets only for parallel items. Bold
      almost never. A table when the same labels repeat.
   4. *Read it as the reader.* Vary sentence length. Join choppy fragments. Split anything you had to
      read twice.
4. **Verify.** Rescan: every high finding is gone or kept on purpose. Then check meaning: every fact,
   number, name, link, command and caveat from the original is still there.
5. **Report** in the format under Output.

## Never change

- Facts, numbers, dates, names, prices, versions, links, commands, code, error text, quoted words.
- What the author thinks. Change tone only when asked ("make it formal").
- Real uncertainty. One honest "probably" stays. Three stacked hedges become one.
- Anything inside code fences, inline code, or someone else's quote.

## Never invent

The fix for a vague claim is never a made-up specific. `significantly faster` with no number becomes
`faster`, not `3x faster`. `Experts agree` with no source gets cut, not cited. When a sentence needs a
fact you don't have, put `[TODO: number?]` in the file (Files mode) or list it under "Needs from you"
(Rewrite mode).

## Don't overcorrect

Slop has an opposite failure mode. Avoid these too:

- Telegraph style: dropped articles, arrows, "w/", stacks of fragments posing as sentences.
- Trading one tic for another, like turning every em dash into a colon or a semicolon. Most should
  become a period.
- Removing structure readers need: numbered setup steps, a reference table, a code sample.
- Curt instead of plain. Keep "please" and "thanks" where a person would say them.
- Restyling someone's voice. Lowercase stays lowercase; slang stays if it's theirs.
- Monotone rhythm. Five eight-word sentences in a row is its own tell.

## House style

These are this user's standing preferences. They apply unless the text's owner says otherwise.

- **No em dashes.** Not in prose, headings, UI copy or commit messages. Use a period, a comma or
  parentheses.
- **Say what it is or does in one short sentence, then stop.** No closing flourish, aphorism or
  `and that's the point`.
- **Nothing hyped.** No launch voice (`excited to announce`), no marketing adjectives, no `game-changer`.
- **No meta-framing.** No `in this post I'll`, `let me walk you through`, or openers that defend an
  earlier choice.
- **Plain technical register for blogs and portfolio copy.** First person, concrete about what was
  built, how, and what broke. Keep lowercase if the source is lowercase.
- **Simple words, short points** when the reader has to act. Lead with the recommendation.
- **Formal when the reader is a customer** (refund or policy emails) or when asked.
- **Commits.** Conventional prefix plus two or three words (`fix: refund retries`, `docs: install table`).
  No body unless the why isn't obvious from the diff. One commit per logical change.
- **PR descriptions.** Short. What changed, what to check, then stop.
- **No AI attribution.** Never a Claude co-author trailer, session trailer or "Generated with" line in
  commits or PRs.

## Dictation mode

The user often dictates. Their drafts have fillers ("uh", "I mean"), restarts, and inline corrections
("10 business templates, sorry, WhatsApp templates"). When cleaning one:

- Keep only the corrected phrase: "10 WhatsApp templates".
- Drop fillers and repeated words. Merge the restarts into one sentence.
- Fix a misheard word only when context makes the intended word certain. Otherwise mark it `[?]`.
- Keep their words, their order of points and their directness. Don't upgrade it into polished AI
  prose. It should sound like them on a good day.
- Don't add points they didn't make, and don't drop ones they did.

Run `scan.py --dictation -` on the draft to find every filler and correction before you start.

## Session mode

When told to unslop yourself, apply Never change, House style and every high-severity rule in
`references/patterns.md` to your own replies for the rest of the session. Don't announce it each time.

## Output

- **Rewrite.** The rewritten text first (fenced if they will copy it). Then at most three short lines:
  what kinds of things changed, and anything under "Needs from you". No itemized change log unless asked.
- **Files and Diff.** Edit in place. One line per file, e.g. `README.md: high 12 -> 0, medium 9 -> 2`,
  plus any tell you kept on purpose and why.
- **Ship.** The final message, ready to paste or commit.
- Never paste the original back.

## Scanner reference

| Flag | Does |
| --- | --- |
| `-` | read stdin (add `--html` if it's HTML) |
| `--diff` | input is a unified diff; scans added lines, and only comments in code files |
| `--commit-msg FILE` | skips `#` lines and the scissors tail; adds subject length, mood and period checks |
| `--dictation` | adds speech filler, self-correction and stutter rules |
| `--format json` | machine-readable findings, counts and score |
| `--min-severity medium` | hide low findings |
| `--strict [--max-score N]` | exit 1 on any high finding (or a score over N) |
| `--allow PHRASE`, `--disable RULE` | per-run exceptions |

Severity: **high** almost never survives a human edit. **Medium** is usually filler and sometimes
earned. **Low** is fine alone and a tell in bulk. The score is weighted findings per 100 words: under
1 is clean, under 3 light, under 8 heavy, above that slop.

**Project config.** A `.unslop.json` in the repo (found by walking up from the working directory)
holds house exceptions and extra rules:

```json
{
  "allow": ["robust"],
  "disable": ["exclamation"],
  "rules": [
    { "id": "old-name", "pattern": "\\boutworld\\b", "severity": "high", "hint": "it's fanpit.live now" }
  ]
}
```

**Suppressions.** `unslop:ignore` anywhere on a line skips it. `<!-- unslop:off -->` and
`<!-- unslop:on -->` skip a region, which is how a style guide can quote bad examples.

**Commit hook.** When the user asks for it, look at `.git/hooks/commit-msg` first and don't overwrite
an existing hook without asking. Then:

```bash
SCAN="$(cd <skill-dir> && pwd)/scripts/scan.py"
printf '#!/bin/sh\nexec python3 "%s" --commit-msg "$1" --strict\n' "$SCAN" > .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

It blocks commits with high-severity tells, including AI co-author trailers. `git commit --no-verify`
skips it once.
