# Genres

Each genre has its own tells and its own idea of "done". Find the genre, apply its rules on top of
the house style in `SKILL.md`.

<!-- unslop:off -->

## Commit messages

- Conventional prefix, then two or three words: `feat: spotlight entries`, `fix: refund retries`,
  `docs: install table`, `chore: bump deps`. Prefixes in use: feat, fix, docs, chore, refactor, perf,
  test, config, ci.
- Imperative, lowercase after the prefix, no trailing period, under 50 characters when possible.
- No body unless the why isn't visible in the diff. When there is one, it explains why, not what.
- One logical change per commit. Split by feature or by file set rather than one big commit.
- No `Co-Authored-By: Claude`, no session trailers, no "Generated with" footer.

> Before: `Added comprehensive retry logic to enhance the robustness of webhook handling.`
> After: `fix: webhook retries`

## Pull request descriptions

- Two parts, both short: what changed (one to four bullets or two sentences) and what to check
  (how to test, what could break).
- No "## Summary / ## Changes / ## Testing" template when each section would hold one line.
- Link the issue. Name the risky file. Skip file-by-file inventories; the diff has them.
- No "This PR introduces". No emoji section headers. No "Generated with Claude Code".

## Changelogs and release notes

- Written for the person upgrading. Lead each line with what they'll notice, not the internal refactor.
- Group by Added, Changed, Fixed, Removed only when there are enough lines to need groups.
- Breaking changes first, with the migration step.
- No "We're excited to announce", no "under the hood improvements" without saying which.

## README

- First line: what it is and who it's for, in one sentence.
- Then install, then the smallest working example, then reference. Most readers stop after the example.
- Commands must be copy-pasteable and correct. Keep every command, flag and path exactly.
- Badges and emoji headers add noise. A table beats bold-label bullets for options.
- No "Features" list of adjectives. Show the feature with an example or cut it.

## Docs and how-to guides

- Task-shaped headings ("Rotate the API key"), not concept-shaped ones ("Understanding keys").
- Numbered steps when order matters. One action per step. Expected output after the step that produces it.
- Define a term once, then use exactly that term.
- Warnings go before the step they apply to, not after.

## Code comments and docstrings

- Comment the why, the constraint or the gotcha. Don't narrate what the next line does.
- No "This function seamlessly handles...". Start with a verb: "Retries the capture up to twice."
- Delete comments that restate the code, mark finished TODOs, or explain an edit ("changed this to fix").
- Keep comments that hold a hard-won fact: "Razorpay sends the webhook before the redirect; don't trust order state here."

## Chat, Slack and WhatsApp messages

- Answer first. Context after, if needed.
- Short. One idea per message. A list only when there are separate items to act on.
- Match the channel's register: lowercase and quick is fine where the author writes that way.
- No sign-offs, no "Hope this helps", no "Let me know if you have questions".

## Customer emails

- Formal and warm, not stiff. Full sentences, a greeting and a sign-off with a real name.
- First paragraph says what happened and what the customer gets (refund amount, date, ticket).
- One clear next step. Dates and amounts exact.
- No legal hedging the policy doesn't require. No "We apologize for any inconvenience this may have caused."

> Before: We sincerely apologize for any inconvenience. Rest assured, your refund has been initiated and will be processed seamlessly.
> After: Your refund of ₹1,499 for Saturday's show was issued today. It should reach your card in 5 to 7 working days.

## Blog posts and portfolio copy

- Plain technical register. First person. What you built, how it works, what broke, what you'd change.
- Open with the thing, not with context or a defense of an old choice. "hi, i'm sanjai" beats a
  paragraph about passion.
- No aphoristic closer, no "and that's the point", no reused ending shape from an earlier post.
- Lowercase stays lowercase if that's the voice. Short sentences, no hype.
- Don't name an employer or day job unless the author does.

## Bios and profiles

- One line on what you do, one on what you've built, one optional personal detail. Concrete nouns over
  adjectives ("built the ticketing backend for fanpit" over "passionate full-stack engineer").

## UI microcopy

- Buttons say exactly what happens: "Issue refund", not "Submit". The toast confirms: "Refund issued".
- Errors say what went wrong and how to fix it. No apologies, no "Oops!".
- Name things the way users know them ("notifications", not "webhook config").
- No exclamation marks in system messages.

## Plans and design docs

- Lead with the recommendation and what happens when it ships, in plain words.
- List everything that will change (files, migrations, templates, env vars). Don't summarize the list away.
- One go unless risk forces stages. If you stage it, say what forces it.
- Open questions come with a recommended default so the reader can just say yes.
- Short readable points beat paragraphs for steps. Paragraphs beat points for reasoning.

<!-- unslop:on -->
