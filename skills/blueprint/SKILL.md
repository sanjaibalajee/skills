---
name: blueprint
description: Turn a text plan into ONE self-contained interactive HTML blueprint reviewed before you code — collapsible steps with reuse/reversibility tags, pan/zoom architecture diagrams whose nodes click through to the relevant section, editable+runnable code playgrounds, file maps, data/API blocks, a risk heatmap, a decision log, wireframes, and reviewer annotations that export back to the agent. Zero dependencies: no MCP, no server, no account; works offline and is shareable as a single file. Use BEFORE implementing work that should be reviewed, compared, or approved — multi-file, ambiguous, risky, or UI-heavy changes — and when an existing text/Markdown plan needs a richer review surface. Skip for trivial one-line fixes. (Prism suite; pairs with `replay`.)
---

# blueprint

Produce a structured, reviewable **blueprint** as a single self-contained HTML file the user
opens in a browser, comments on, and approves — *before* any code is written. The blueprint is the
approval gate and the source of truth, not the chat.

The artifact is **interactive in the browser**: architecture diagrams pan/zoom and their nodes can link
to the section they describe; code snippets can be **editable + runnable** playgrounds; reviewers
annotate any block and export the notes back to you. All in one file, no server.

Unlike hosted planning tools, this skill has **no external dependency**: the artifact is one HTML
file with the structured plan model embedded as JSON inside it. That file is at once the
human-viewable document, the machine-readable model (you re-read it to apply feedback), and a
portable thing the user can commit to the repo or send over chat. It works offline forever.

## When to use / skip

**Use it** whenever a plan is better as a reviewable artifact than a chat paragraph: multi-file or
multi-step work, ambiguous or risky changes, a UI surface with states, an API/data-shape decision
that needs alignment, or when an existing text plan needs a richer review surface.

**Skip it** for truly trivial, unambiguous work — typos, one-line fixes, a single well-specified
function. Just make the change. Never pad a plan with filler and never ship a single-step plan.

## Workflow

1. **Research first — never invent.** Read the real files, schemas, actions, and patterns. Name
   actual files, symbols, and data shapes. For each step, lead with what it **reuses** (existing
   functions, components, schema) before what it **adds**. Delegate wide exploration to a subagent
   when the surface is large. Planning is **read-only** — make no source edits until the user approves.

2. **Decide the hard-to-reverse bets first.** For backend/data/API work, call out decisions that are
   expensive to undo once callers or data depend on them — wire format, public ids, data-model shape,
   auth/ownership boundaries — and get those right in the plan. Capture each as a `decision` block with
   its reversibility flag. Then scope the smallest first cut that proves the approach; state what's in
   and what's explicitly deferred.

3. **Read the block catalog.** Open `references/BLOCKS.md` (relative to this skill) for the authoritative
   block vocabulary and the model schema. Author from it, not from memory — unknown block types render
   as an error box.

4. **Author the model JSON.** Build a `{ "kind":"plan", ... }` model (see schema below). A good plan is:
   - **Outcome-first**: `summary` says what changes and why, in product terms, before mechanics.
   - **Spined on `steps`**: each step has a status (`planned` to start), `reuses`/`adds`/`files`, and a
     `reversibility` flag where it matters.
   - **Concrete near the top**: for UI/product work lead with a `wireframe` of the real app state; for
     architecture lead with one `diagram` and wire its nodes to the relevant sections via `links`. Add
     `datamodel`/`api` blocks next to the prose that needs them.
   - **Lean on interactivity where it pays**: give an architecture `diagram` `links` so reviewers click a
     node to jump to its section; make the one tricky algorithm an `editable`+`runnable` `code` block so
     they can poke at it. Don't sprinkle these everywhere — use them on the thing worth exploring.
   - **Honest about risk**: include a `risk` heatmap for non-trivial work, and a single `questions` block
     near the bottom for anything genuinely unresolved (decide what you can; recommend a default for the rest).
   - **Lean, not thin.** A handful of focused blocks, no filler.

5. **Build the artifact.**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/build.py plan-model.json -o PLAN.html        # lean (diagrams shown as source)
   python3 ${CLAUDE_SKILL_DIR}/scripts/build.py plan-model.json -o PLAN.html --fetch-mermaid   # offline diagram rendering
   ```
   Write the model JSON next to where the user wants it (e.g. `plans/<slug>/plan-model.json`) and the
   HTML beside it. Keep the JSON — it's the editable source you'll patch on feedback.

6. **Surface it and request approval.** Give the user the absolute path to the `.html` file and tell
   them to open it (the file opens directly in any browser — no server). Name which files/areas the
   work will touch. Presenting the plan and asking for sign-off **is** the approval step — don't ask a
   separate "does this look good?". Do not start coding until they approve.

7. **Apply feedback via the model, not the chat.** Reviewers turn on **✎ Annotate**, click any block to
   leave a note, then **⧉ Copy** (or **⬇ JSON**) to hand the notes back to you. Read those notes, edit
   `plan-model.json`, and rebuild. The document — not the chat — stays the source of truth. Re-read the
   approved plan before major implementation steps.

## Self-review before handoff (high-stakes plans only)

For architecture/backend/data/migration/multi-file plans, run one quick adversarial pass after building:
spawn a skeptical subagent whose only job is to find what's weak, missing, or wrong — unanchored steps,
a hard-to-reverse decision made implicitly, a menu of options where the plan should commit, single-step
filler. Apply clear fixes to the JSON yourself and rebuild; route genuine judgment calls into the
`questions` block. Skip this for small or single-decision plans.

## Model schema (quick reference)

See `references/BLOCKS.md` for the full catalog. Skeleton:

```jsonc
{
  "kind": "plan",
  "id": "stable-slug",
  "title": "Imperative one-liner",
  "subtitle": "optional context",
  "meta": { "repo": "...", "branch": "...", "author": "...", "date": "YYYY-MM-DD" },
  "summary": "Outcome-first markdown.",
  "blocks": [
    { "type": "metrics", "items": [ /* scope at a glance */ ] },
    { "type": "heading", "level": 2, "text": "Approach" },
    { "type": "steps", "items": [ /* the spine; reuses/adds/files/reversibility */ ] },
    { "type": "decision", "choice": "...", "reversibility": "hard", "alternatives": ["..."], "rationale": "..." },
    { "type": "diagram", "title": "Architecture", "mermaid": "flowchart LR ..." },
    { "type": "risk", "items": [ /* blast radius */ ] },
    { "type": "heading", "level": 2, "text": "Open questions" },
    { "type": "questions", "items": [ /* decide what you can; recommend defaults */ ] }
  ]
}
```

## Rules

- **Grounding:** real files/symbols/data only; redact secrets (`sk-•••`). Read before you draft.
- **Read-only until approval.** No edits to source while planning.
- **The document is the source of truth.** On scope change, update the model JSON and rebuild — don't
  only pivot in chat. Keep one bottom `questions` block for the unresolved.
- **When the artifact looks wrong, fix the renderer/skill** (`scripts/template.html`), never hand-edit
  one output `.html`. Turn feedback into better guidance.
