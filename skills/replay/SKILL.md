---
name: replay
description: "Turn a finished diff, PR, branch, or commit range into ONE self-contained interactive HTML replay of the change — outcome narrative, file map with change flags, annotated diffs you can flip between split/unified with word-level highlights, a pan/zoom architecture diagram whose nodes click through to the relevant diff, a risk/blast-radius heatmap, and a PLAN-VS-REALITY DRIFT tracker that flags where the code deviated from the original plan (as-planned / changed / skipped / unplanned). Plus reviewer annotations that export back to the agent. Zero dependencies: no MCP, no server, no account; works offline and is shareable as a single file. Use to summarize completed work for review at a higher level than line-by-line, before or alongside a PR. (Prism suite; pairs with `blueprint`.)"
---

# replay

Produce a **replay** of completed work as a single self-contained HTML file: a plan built *from*
a diff, not toward one. It helps a reviewer understand the **shape** of a change — outcome, file map,
the few diffs that matter, risk, and how reality compared to the plan — before they dive into raw code.

The diffs are **interactive**: split/unified toggle, word-level intra-line highlights, collapsible
context, copy buttons; the architecture diagram pans/zooms and its nodes jump to the diff they describe.

Like `blueprint`, the artifact is one HTML file with the recap model embedded as JSON. No MCP, no
server, no account. Commit it next to the PR, or send it as one file.

## The standout: plan-vs-reality drift

If an original `blueprint` artifact exists for this work (a `*-model.json` with `"kind":"plan"`, or the
plan the user references), **load it and compute drift**: walk its `steps`/`decision` blocks against what
the diff actually did, and emit a `drift` block classifying each item as `as-planned`, `changed`,
`skipped`, or `added` (unplanned). This accountability layer is the reason to reach for this skill over a
plain PR description. If there is no prior plan, skip the `drift` block — don't fabricate one.

## Workflow

1. **Collect the diff from real sources.** Use the actual change set — don't infer it:
   ```bash
   git diff main...HEAD                 # branch vs base
   git show <sha>                       # single commit
   git diff <base>..<head> --stat       # file map + churn
   gh pr diff <number>                  # a GitHub PR
   ```
   Read the touched files for context. Every block must derive mechanically from this diff —
   real paths, fields, methods, and before/after text only.

2. **Read the block catalog.** Open `references/BLOCKS.md` for the authoritative vocabulary and schema.
   Author from it, not memory.

3. **Author the model JSON** (`{ "kind":"recap", ... }`). Canonical recap shape, top to bottom:
   - `metrics` — files changed, +/− lines, new deps, risk at a glance.
   - `summary` (top-level field) — 1–3 paragraph outcome narrative: what shipped and why it matters.
   - `drift` — plan-vs-reality, **if a prior plan exists** (see above).
   - `diagram` — an **auto architecture diagram**: derive a Mermaid flow/sequence from the real
     import/call relationships the diff introduces or changes (not hand-waved boxes).
   - `filetree` — every changed file with `change` flag and `plus`/`minus` churn; one-line `note` on the
     non-obvious ones.
   - `tabs` (label "Key changes") — 3–8 focused `diff` blocks, each with a `note` saying *why* the hunk
     matters. Show the lines that explain the change, not the whole patch.
   - `risk` — blast-radius heatmap: score each touched file (churn × fan-in/out × test-coverage gaps ×
     how critical the path is), with reasons and mitigation.
   - `datamodel` / `api` — only if schema or endpoints changed.
   - `decision` — any non-obvious choice the diff embodies, with rationale and reversibility.
   - `questions` — anything left open for the reviewer.

   **Lean is not thin.** Keep it scannable, but include enough real diff/file evidence that the reader
   trusts it. A recap that's all headlines and no code is a defect.

4. **Build the artifact.**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/build.py recap-model.json -o RECAP.html
   python3 ${CLAUDE_SKILL_DIR}/scripts/build.py recap-model.json -o RECAP.html --fetch-mermaid   # offline diagram rendering
   ```

5. **Surface it.** Give the user the absolute path to the `.html`. It opens in any browser, no server.

6. **Annotation round-trip.** Reviewers turn on **✎ Annotate**, click blocks to leave notes, then
   **⧉ Copy** / **⬇ JSON** to hand them back. Read the notes; if they require code changes, make them and
   regenerate the recap from the new diff so the artifact stays true to reality.

## Rules

- **Grounding is mechanical.** Real paths, fields, methods, before/after text — derived from the diff,
  never inferred or invented. Read the files.
- **Redact secrets** in every block and prose (`sk-•••`, `<redacted>`).
- **Drift must be honest.** Surface skipped and unplanned work, not just the wins — that's the whole point.
- **A recap reflects reality.** If code changes after review, regenerate from the new diff; don't hand-edit
  the output `.html`. When the renderer looks wrong, fix `scripts/template.html`, not one artifact.
