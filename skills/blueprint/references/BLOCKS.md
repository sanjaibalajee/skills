# Block catalog — authoritative model schema

This is the single source of truth for the artifact model consumed by `shared/build.py`
and rendered by `shared/template.html`. **Author models from this file, not from memory.**
If you reach for a block that isn't here, it doesn't exist — add prose instead.

## Top-level model

```jsonc
{
  "kind": "plan" | "recap",          // drives the hero label + defaults
  "id": "stable-slug",               // used to namespace saved review notes; keep stable across rebuilds
  "title": "Imperative one-liner",
  "subtitle": "optional one-line context",
  "meta": { "repo": "...", "branch": "...", "base": "...", "author": "...", "date": "YYYY-MM-DD" },
  "summary": "Outcome-first markdown. 1–3 short paragraphs. What & why, not how.",
  "blocks": [ /* ordered array of the blocks below */ ]
}
```

`meta` keys are free-form — every non-empty key renders as a chip. `summary` and every `md`
field accept lightweight markdown: `#`–`####` headings, `**bold**`, `*italic*`, `` `code` ``,
`- ` / `1. ` lists, ` ```fenced``` ` code, and `[links](url)`.

## Blocks

Each block is `{ "type": "<name>", ...fields }`. Every block (except `heading`) is annotatable.

### `heading` — section anchor + TOC entry
`{ "type":"heading", "level":2|3, "text":"Section", "id":"optional-slug", "md":"optional intro" }`
Only `level:2` headings appear in the left nav. Use these to structure the document.

### `prose` — markdown body
`{ "type":"prose", "md":"..." }`

### `callout` — boxed note
`{ "type":"callout", "variant":"info|warn|success|danger", "title":"optional", "md":"..." }`

### `metrics` — KPI tiles (great as the first block)
`{ "type":"metrics", "items":[ { "label":"Files", "value":"7", "delta":"5 mod · 2 new", "intent":"good|bad|warn|neutral" } ] }`

### `steps` — plan/implementation steps (the spine of a plan)
```jsonc
{ "type":"steps", "items":[ {
  "title":"Step title",
  "status":"planned|in-progress|done|skipped|blocked",
  "reversibility":"hard|soft",            // optional — flag hard-to-undo bets
  "md":"detail",
  "reuses":["existing/file.py:fn","Component"],   // lead with reuse
  "adds":["new symbol"],
  "files":["path/a.ts","path/b.ts"]
} ] }
```
Steps are collapsible; click to expand `md`/tags. `reuses` render as ♻ green, `adds` as + blue.

### `checklist` — simple done/not-done list
`{ "type":"checklist", "items":[ {"label":"...","done":true} ] }`

### `diagram` — Mermaid (architecture, sequence, ERD, flow) — **interactive**
`{ "type":"diagram", "title":"...", "mermaid":"flowchart LR\n A-->B", "links":{ "NodeLabel":"target-id" } }`
Renders client-side and is **pan/zoom + fullscreen** in the browser. Optional `links` maps a node's
visible label (exact or substring) to a block `id` or `heading` id — clicking that node scrolls to and
flashes the target (and opens its tab if it's inside one). Use this to wire an architecture diagram to the
diffs/sections it refers to. For offline rendering build with `--fetch-mermaid`; otherwise the source shows
in a code box.

### `filetree` — changed files with flags + churn
`{ "type":"filetree", "root":"repo", "entries":[ {"path":"a/b.py","change":"add|mod|del|ren","plus":12,"minus":3,"note":"..."} ] }`

### `diff` — annotated before/after (the heart of a recap)
```jsonc
{ "type":"diff", "file":"path", "lang":"python", "note":"why this hunk matters",
  "hunks":[ { "header":"@@ -41,6 +41,9 @@ def login():", "lines":[
    {"type":"ctx","text":"unchanged line"},
    {"type":"del","text":"old line"},
    {"type":"add","text":"new line"}
  ] } ] }
```
Keep diffs focused: 3–8 hunks total across the recap, not the whole patch. Show the lines that explain the change.
**Interactive in the browser:** every diff has a **Copy** button and a **Split ⊟ / Unified ▤** toggle,
shows **word-level intra-line highlights** on changed lines, and **collapses long runs of unchanged
context** behind a click-to-expand row. You just supply the hunks — the interactivity is automatic.

### `code` — a single snippet (not a diff) — **optionally live**
`{ "type":"code", "file":"optional", "lang":"ts", "text":"...", "note":"optional md", "runnable":true, "editable":true }`
Always has a **Copy** button and line numbers. Add `"runnable":true` (for `lang` html/js/javascript/css)
to get a **▶ Run** button that executes the snippet in a sandboxed iframe and shows the output inline
(`console.log` is captured). Add `"editable":true` to render it as an editor the reviewer can tweak before
running — a real playground inside the artifact. Use sparingly, for the one snippet worth poking at.

### `datamodel` — entities/fields table
`{ "type":"datamodel", "entities":[ {"name":"User","fields":[{"name":"id","type":"uuid","note":"pk"}]} ] }`

### `api` — endpoint table
`{ "type":"api", "endpoints":[ {"method":"POST","path":"/login","desc":"..."} ] }`
`method` colors: GET/POST/PUT/PATCH/DELETE.

### `decision` — decision log with rationale + reversibility
`{ "type":"decision", "choice":"What we chose", "reversibility":"hard|soft", "alternatives":["A","B"], "rationale":"md — why" }`
Use for hard-to-reverse bets (wire format, public ids, data shape, auth/ownership).

### `risk` — blast-radius heatmap (auto-sorted by score, colored bars)
`{ "type":"risk", "items":[ {"file":"path","score":0-100,"reasons":["churn","hot path"],"mitigation":"..."} ] }`
Score ≥70 red, 40–69 amber, <40 green. Score from churn × fan-in/out × test coverage gaps × criticality.

### `drift` — plan-vs-reality (RECAP ONLY; the standout feature)
`{ "type":"drift", "items":[ {"planned":"...","actual":"...","status":"as-planned|changed|skipped|added","severity":"low|med|high","note":"..."} ] }`
Renders a summary strip (✓ as planned · ≠ changed · ✗ skipped · + unplanned) then per-item rows.
Populate by diffing the original plan artifact's `steps` against what the diff actually did.

### `wireframe` — sandboxed HTML mock (UI plans/recaps)
`{ "type":"wireframe", "title":"...", "height":420, "html":"<div>...</div>" }`
Rendered in a `sandbox=""` iframe (no scripts). Use real product content, neutral grey-box styling. Inline `style=""` only; no `<html>`/`<head>`.

### `questions` — open questions with recommended defaults
`{ "type":"questions", "items":[ {"q":"...","options":["A","B"],"recommendation":"A"} ] }`
Put ONE of these near the bottom. Decide what you can; recommend a default for the rest.

### `tabs` — group blocks under tabs (e.g. "Key changes")
`{ "type":"tabs", "tabs":[ {"label":"file.py","blocks":[ /* any blocks above */ ]} ] }`
Tabs can nest any block type, including `diff`/`code`/`diagram`.

### `divider`
`{ "type":"divider" }`

## Grounding rules (non-negotiable)

- **Real paths, symbols, and code only.** Every `diff`, `filetree`, `code`, `datamodel`, and `api`
  field must come from the actual repo/diff — never invented. Read the files first.
- **Redact secrets.** Never put API keys, tokens, or credentials in any field. Use `sk-•••` / `<redacted>`.
- **Lean, not thin.** A handful of focused blocks beats a wall. But include enough evidence (real diffs,
  real file map) that a reader trusts it — visual headlines with no substance is a defect.
