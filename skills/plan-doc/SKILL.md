---
name: plan-doc
description: Write a plan as one clean, self-contained HTML document that people can read, review and approve. It leads with the recommendation, says in plain words what happens when it ships, lists every file, migration, template and env var that changes, and ends with open questions that each carry a recommended answer. House design with light and dark themes, hairlines instead of cards, one purple accent, phone-friendly, no build step and no network. Use when the user asks for a plan doc, design doc, proposal, RFC, one-pager, scope doc, migration or rollout plan, a progress or audit report, or to "write up the plan" for teammates, clients or later. For an interactive pre-coding approval gate built from a JSON model, use blueprint instead.
---

# plan-doc

Write the plan as a document a busy person can read in three minutes and answer with "yes". One
`.html` file: it opens in any browser, survives being sent over chat, and can be published as an
artifact when the session has a tool for that.

`<skill-dir>` below is the folder holding this file. Claude Code exposes it as `${CLAUDE_SKILL_DIR}`.

## Use it or skip it

Use it when the plan will be read by someone other than you right now: a teammate, a client, the
user tomorrow. Typical asks: "write up the plan", "make a design doc", "scope this", "proposal for X",
"plan the migration", "status of each issue".

Skip it for a one-step change, or when the user wants the plan in chat. If they want a code-level
approval gate with diffs, playgrounds and annotations, that's `blueprint`.

## Workflow

1. **Research first. Planning is read-only.** Read the real code, schemas, configs and docs. Name
   actual files, functions, tables and env vars. Don't edit source, and don't run builds, tests or
   deploys while planning unless the user asks.
2. **Decide before you write.** Pick the recommendation. Plan it in one go; split into stages only if
   risk forces it, and say what forces it. Decide what's out of scope. Anything you can't decide
   becomes an open question with a recommended answer.
3. **Scaffold.**
   ```bash
   python3 <skill-dir>/scripts/plandoc.py new "Webhook retries" --out plans/
   ```
   It copies `assets/template.html` to `plans/webhook-retries.html` and fills the title, date,
   author, repo and branch from git. Use `--out` with a `.html` path to choose the exact file.
4. **Fill it.** Replace every `[[...]]` placeholder. Pull optional blocks (decisions, risks, status,
   diagram, out of scope, timeline) from `references/components.md`, in the order listed there.
   Delete the guidance comments as you go.
5. **Check.**
   ```bash
   python3 <skill-dir>/scripts/plandoc.py check plans/webhook-retries.html
   ```
   Fix every error. Fix warnings unless you have a reason. If the `unslop` skill sits next to this
   one, `check` also scans the prose. Treat its findings as edits to make.
6. **Hand it over.** Give the absolute path, the recommendation in one line, and what you need from
   the user. Presenting the doc is the approval request. Don't ask "does this look good?" separately.
   Don't start the work until they approve.
7. **Keep it current.** On feedback or scope change, edit the same file, move the status pill
   (`draft`, `in-review`, `approved`, `in-progress`, `done`, `dropped`) and add a changelog line.
   The doc is the source of truth, not the chat. Re-read it before big implementation steps.

## What makes it good

- **Recommendation first.** One call, stated plainly, with what you need from the reader. The user
  tends to reply "what would you recommend?", so answer that before they ask.
- **Plain words, short points.** "What happens when this ships" is written for someone who won't
  read the code: what users see, what changes in production, what could break.
- **Complete inventory.** The changes table lists every file, migration, template, env var, cron,
  queue and dependency the work touches. Nothing hidden behind "and related files".
- **Grounded.** Real paths in `<code>`. Real numbers or none. Secrets redacted (`rzp_live_•••`).
- **Every question has a default.** "Recommended: X, because Y" so the reader can just say yes.
- **Lean.** A short plan is a good plan. No filler sections, no single-step plans, no invented
  timeline. Delete any optional block that would hold one line of nothing.
- **Unslopped.** No em dashes, no hype, no "robust" or "seamless", no closing flourish. Say what a
  thing does and stop. The `unslop` skill's rules apply to every sentence.

## Design rules

The template carries the house style. Keep it consistent across docs:

- One reading column, left-aligned text, about 70 characters wide. Sections split by hairlines.
- No cards, shadows, gradients, rounded panels or tinted boxes (code blocks excepted).
- Purple marks the recommendation and nothing else. Status colors (green, amber, red) only on tags
  and the status pill.
- Hierarchy comes from size, weight and spacing. Labels are lowercase mono, never uppercase eyebrows.
- Body text 17px, line height around 1.6. Readability wins over density.
- Light and dark both work: every color is a token on `:root`, redefined in the two dark blocks.
  Never write a color literal in a component rule.
- Works at phone width, offline, and in print. No web fonts; the system stacks are deliberate.
- Title is the plan's name in two to five words ("Webhook retries", "Hosting tab scope"). No
  "Plan:" prefix, no explanation after a dash or colon. The lede explains.

To change the house style, edit `assets/template.html` (tokens first), not one output file.

## Publishing as an artifact

When the session has an artifact publishing tool and the doc is meant for other people, offer to
publish it, or publish it if the user asked for a link. Those hosts wrap the page in their own
skeleton, so publish the fragment:

```bash
python3 <skill-dir>/scripts/plandoc.py fragment plans/webhook-retries.html
# writes plans/webhook-retries.artifact.html: no doctype, html, head or body tags; mermaid loader removed
```

Keep the `.html` as the source. Regenerate the fragment after each edit and republish to the same
URL. Without such a tool, the local file is the deliverable.
