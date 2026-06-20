# Prism — `blueprint` + `replay`

Two Claude skills that turn planning and change-review into **one self-contained interactive HTML file**
each — no MCP, no server, no account, no internet at view time.

- **`blueprint`** *(look forward)* — turn a text plan into a reviewable artifact *before* you code:
  collapsible steps with reuse/reversibility tags, pan/zoom architecture diagrams, **editable + runnable
  code playgrounds**, file maps, data/API blocks, a risk heatmap, a decision log, wireframes. The
  blueprint is the approval gate.
- **`replay`** *(look back)* — turn a finished diff/PR/branch into an interactive review *after* the fact:
  outcome narrative, file map, **split/unified diffs with word-level highlights**, an auto architecture
  diagram whose nodes jump to the relevant diff, a risk/blast-radius heatmap, and a **plan-vs-reality
  drift tracker** that flags where the code deviated from the original `blueprint`.

The output is one `.html` you double-click to open in any browser, commit to the repo, or send over chat.
The structured model lives as JSON *inside* the file, so it's at once a human-viewable document, a
machine-readable model the agent re-reads, and a git-diff-friendly artifact.

---

## Install

Each skill is **self-contained** (it bundles its own `scripts/` and `references/`), so installing is just
copying a folder.

**Quick install (both skills):**

```bash
git clone https://github.com/sanjaibalajee/skills.git
cd skills
./install.sh                 # user-level: ~/.claude/skills
./install.sh /path/to/repo   # project-level: <repo>/.claude/skills
```

**Or copy a single skill by hand:**

```bash
cp -R skills/blueprint ~/.claude/skills/blueprint
```

**On Claude.ai** — zip a skill folder and upload it under *Settings → Capabilities → Skills*:

```bash
cd skills && zip -r blueprint.zip blueprint
```

After any of these, run `/skills` in Claude Code (or restart) to pick them up.

---

## Use

Just ask, in natural language — the skills self-trigger:

- *"Plan how I'd add per-IP rate limiting to the auth endpoints before I touch code."* → `blueprint`
- *"Give me a visual recap of the changes on this branch vs main."* → `replay`

Each produces a `.html` and tells you the path. Open it, review, and (in annotate mode) leave notes that
export back to the agent.

### In the browser

- **Left nav** auto-built from headings, with scroll-spy. **Search** (`/`) filters live. **◐** theme,
  **⎙** print to PDF.
- **Interactive diagrams** — drag to pan, scroll to zoom, fullscreen; click a wired node to jump to its
  section/diff.
- **Interactive code** — diffs have Copy + **Split ⊟ / Unified ▤**, **word-level** highlights, and
  collapsible context. `code` blocks can be **▶ Run** + **editable** playgrounds (sandboxed iframe).
- **Annotation loop** — **✎ Annotate** → click a block → leave a note → **⬇ JSON** / **⧉ Copy** hands
  notes back to the agent. No server.

---

## Repo layout

```
skills/
  blueprint/           # self-contained skill — install this alone if you want
    SKILL.md
    scripts/           # build.py + template.html (the renderer)
    references/        # BLOCKS.md (the model schema)
  replay/              # same shape
examples/              # sample-plan / sample-recap (.json source + .html artifact)
install.sh             # copies the skills into your Claude skills dir
```

Each skill carries its own copy of `scripts/build.py` + `scripts/template.html` so it installs
independently. If you edit the renderer in one, mirror it to the other:

```bash
cp skills/blueprint/scripts/* skills/replay/scripts/
```

## How it works

The source of truth is a structured **model JSON** (see `skills/*/references/BLOCKS.md` for the catalog).
`scripts/build.py` (pure stdlib) embeds it inside `scripts/template.html` (a zero-dependency renderer) to
produce one portable `.html`:

```bash
python3 skills/blueprint/scripts/build.py examples/sample-plan.json -o plan.html
python3 skills/replay/scripts/build.py    examples/sample-recap.json -o recap.html --fetch-mermaid
```

Mermaid is inlined only for artifacts that actually have diagrams (`--fetch-mermaid`, cached in `vendor/`,
git-ignored); diagram-free artifacts stay ~35–50 KB.

## License

MIT © 2026 Sanjai Balajee — see [LICENSE](LICENSE).
