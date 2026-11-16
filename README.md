# skills

Skills for coding agents: Claude Code, Codex, Cursor and anything else that reads `SKILL.md`.
Each skill is one folder, and you can install any of them on its own.

| skill | what it does |
| --- | --- |
| [unslop](skills/unslop/SKILL.md) | Rewrites text so it reads like a person wrote it. A bundled scanner flags AI tells by line in Markdown, HTML, commit messages and diffs. |
| [plan-doc](skills/plan-doc/SKILL.md) | Writes a plan as one clean HTML doc that leads with the recommendation and lists everything that changes. |
| [blueprint](skills/blueprint/SKILL.md) | Turns a plan into an interactive HTML approval gate before you write code. |
| [replay](skills/replay/SKILL.md) | Turns a finished diff into an interactive review and shows where the work drifted from its blueprint. |
| [pr-ready](skills/pr-ready/SKILL.md) | Takes a change to a ready-to-merge PR with nobody watching: proves it, gets it reviewed, files it, babysits it. You merge. |
| [pr-merge](skills/pr-merge/SKILL.md) | pr-ready, then merges once every gate passes, never around branch protection. |
| [pr-babysit](skills/pr-babysit/SKILL.md) | Babysits an open PR: CI, review bots, reviewers, a stale base. A bundled watcher wakes the agent once per real event. |
| [cross-model-review](skills/cross-model-review/SKILL.md) | Has a different model (Codex by default) review a change in a loop until it runs out of real objections. Panel mode runs three. |
| [pr-revive](skills/pr-revive/SKILL.md) | Revives a stale PR: decides REBASE, REWRITE or CLOSE, then rebases it safely. |
| [android-compose](skills/android-compose/SKILL.md) | Android rules for Kotlin and Jetpack Compose, condensed from 17 Google and community skills. |
| [ios-swiftui](skills/ios-swiftui/SKILL.md) | SwiftUI rules for iPhone apps on iOS 26+ and Swift 6, from a shipping app and the top SwiftUI skills. |

## Install

### Any agent, one skill at a time

```bash
npx skills add sanjaibalajee/skills --skill unslop
npx skills add sanjaibalajee/skills --skill plan-doc
npx skills add sanjaibalajee/skills --skill blueprint
npx skills add sanjaibalajee/skills --skill replay
npx skills add sanjaibalajee/skills --skill pr-ready
npx skills add sanjaibalajee/skills --skill pr-merge
npx skills add sanjaibalajee/skills --skill pr-babysit
npx skills add sanjaibalajee/skills --skill cross-model-review
npx skills add sanjaibalajee/skills --skill pr-revive
npx skills add sanjaibalajee/skills --skill android-compose
npx skills add sanjaibalajee/skills --skill ios-swiftui
```

`pr-ready` uses `pr-babysit` and `cross-model-review`, and `pr-merge` uses `pr-ready`, so install the
four together: `npx skills add sanjaibalajee/skills --skill pr-ready pr-merge pr-babysit cross-model-review`.

Add `-g` to install for every project instead of the current one, and `-a claude-code` (or `codex`,
`cursor`) to choose the agent. `npx skills add sanjaibalajee/skills --list` shows what's here.

### Claude Code plugin

```text
/plugin install unslop --marketplace sanjaibalajee/skills
/plugin install plan-doc --marketplace sanjaibalajee/skills
/plugin install blueprint --marketplace sanjaibalajee/skills
/plugin install replay --marketplace sanjaibalajee/skills
/plugin install pr-ready --marketplace sanjaibalajee/skills
/plugin install pr-merge --marketplace sanjaibalajee/skills
/plugin install pr-babysit --marketplace sanjaibalajee/skills
/plugin install cross-model-review --marketplace sanjaibalajee/skills
/plugin install pr-revive --marketplace sanjaibalajee/skills
/plugin install android-compose --marketplace sanjaibalajee/skills
/plugin install ios-swiftui --marketplace sanjaibalajee/skills
```

On older Claude Code versions, add the marketplace first with `/plugin marketplace add sanjaibalajee/skills`,
then run `/plugin install unslop@sanjaibalajee-skills`.

### From a clone

```bash
git clone https://github.com/sanjaibalajee/skills.git && cd skills
./install.sh unslop plan-doc            # these two, into ~/.claude/skills
./install.sh --project ~/code/app       # every skill, into that repo's .claude/skills
./install.sh --dest ~/.agents/skills    # any skills directory
./install.sh --link unslop              # symlink, so edits here show up everywhere
./install.sh --list                     # what's available
```

### Claude.ai

Zip a skill folder and upload it under *Settings > Capabilities > Skills*:

```bash
cd skills && zip -r unslop.zip unslop
```

After installing, run `/skills` in Claude Code or restart it.

## unslop

Ask for it in plain words:

- "unslop this" with pasted text
- "unslop the README"
- "unslop the docs I changed on this branch"
- "clean up this message, I dictated it"
- "unslop yourself" to keep your agent's replies plain for the rest of the session

It rewrites in passes (cut, make concrete, fix the shape, read as the reader), keeps every fact,
number, link and command, and won't invent a number to replace a vague claim. Its house rules: no em
dashes, no hype, no closing flourishes, short conventional commits with no AI co-author trailers.

The scanner also works without the agent:

```bash
python3 skills/unslop/scripts/scan.py README.md
git diff main | python3 skills/unslop/scripts/scan.py --diff -
python3 skills/unslop/scripts/scan.py --commit-msg .git/COMMIT_EDITMSG --strict
```

Put a `.unslop.json` in a repo for house exceptions and extra banned words. The skill can also
install a `commit-msg` hook that blocks sloppy commit messages. See
[examples/unslop](examples/unslop) for a before and after.

## plan-doc

Ask for "a plan doc for X", "a design doc", "write up the plan" or "status of each issue". It reads
the code first, then writes `plans/<slug>.html` in this order: the recommendation, what happens when
it ships, every file and setting that changes, steps, decisions, risks, and open questions that each
carry a recommended answer.

The doc is one HTML file with light and dark themes that works on a phone. It needs no network and
has no build step. `plandoc.py check` lints placeholders, title, theme tokens and prose. When the
session can publish artifacts, `plandoc.py fragment` makes a copy ready to publish. See
[examples/plan-doc/webhook-retries.html](examples/plan-doc/webhook-retries.html).

## blueprint and replay

Both produce one self-contained interactive HTML file with the structured model embedded as JSON, so
the file is the document, the machine-readable source and a shareable artifact at once.

- **blueprint** runs before coding. It turns a plan into collapsible steps with reuse and
  reversibility tags, pan and zoom architecture diagrams, editable and runnable code playgrounds,
  file maps, data and API blocks, a risk heatmap, a decision log and wireframes. The blueprint is
  the approval gate.
- **replay** runs after. It turns a diff, PR or branch into an outcome summary, a file map, split
  or unified diffs with word-level highlights, a risk heatmap and a drift tracker that compares what
  shipped against the original blueprint.

In the browser you get a nav built from headings with live search (`/`), a theme toggle, print,
diagrams whose nodes jump to the matching section or diff, and an annotate mode that exports
reviewer notes as JSON for the agent to apply.

```bash
python3 skills/blueprint/scripts/build.py examples/blueprint/plan.json -o plan.html
python3 skills/replay/scripts/build.py examples/replay/recap.json -o recap.html --fetch-mermaid
```

`build.py` is stdlib only. `--fetch-mermaid` downloads Mermaid once into `vendor/` (git-ignored) so
diagrams render offline. Files without diagrams stay around 35 to 50 KB. The two skills carry
identical copies of the renderer so each installs alone; after editing blueprint's copy, run
`python3 tools/validate.py --sync` to update replay's.

## PR workflow: pr-ready, pr-merge, pr-babysit, cross-model-review, pr-revive

Skills for getting work merged without watching it. Trigger them by name. They need an authenticated
`gh`.

pr-ready is for when you aren't going to watch. The agent finishes the change on a branch, proves it
with evidence it saw (a reproduction, the checks CI runs, the app running), gets a second model's
review, files a short PR that leads with the problem, and babysits CI and the review bots until the
PR is ready. Then it stops and you merge. Asking for it is permission to run the builds and device
checks the proof needs, even if your `AGENTS.md` says to ask first. pr-merge does the same and then
merges with your repo's merge method once the gate passes, never with `--admin` or around branch
protection.

pr-babysit ships `scripts/pr_watch.py`, which polls GitHub and prints one line per real event (a
failed check, a new review, a push by someone else, the base moving), so a Claude Code `Monitor`
wakes the agent only when something happened. It checks bot findings against the code before
changing anything and keeps the PR at its original size.

cross-model-review runs `codex exec -s read-only` as the reviewer (or another provider, or a fresh
subagent), keeps a ledger of findings by severity, and argues it out for up to three rounds. Panel
mode runs three reviewers from different providers with scores out of 10.

pr-revive checks what changed on the base since a stale PR branched and gives one verdict: REBASE
(rebase, test, push with a lease), REWRITE (the goal holds, the code doesn't) or CLOSE
(superseded). It never merges, and closes only with your OK.

```bash
python3 skills/pr-babysit/scripts/pr_watch.py 123 --until ready    # 0 ready, 1 act, 2 bad input, 3 timed out
```

## Mobile: android-compose and ios-swiftui

House rules for native mobile apps. Each rule corrects a mistake agents make, with a short SKILL.md
and references the agent loads per topic.

android-compose condenses 17 skills into one: Google's official Navigation 3, edge-to-edge, adaptive,
Compose performance, AGP 9, testing and security skills, plus rcosteira79's Compose, data layer,
Retrofit, Coil, testing, Gradle and modularization skills. It covers the app's module shape, a Route
and Screen split, repositories as the error boundary, Compose traps, insets and the keyboard,
Navigation 3, AGP 9, tests and security.

ios-swiftui covers SwiftUI on iOS 26+ with Swift 6.2 and main actor by default: a package of feature
modules with a router per tab, state ownership and Observation traps, list identity, concurrency,
Liquid Glass, iOS 27 toolbars, iPhone Duo layouts, lenient decoding and Swift Testing. It draws on a
shipping app's lessons and on the top public SwiftUI skills (AvdLee, twostraws, Dimillian), and
leaves out the rules they get wrong.

Both put the project's own `AGENTS.md` or `CLAUDE.md` first and default to "don't build until asked".

## Repo layout

```text
skills/<name>/          one folder per skill; this is what gets installed
  SKILL.md              frontmatter (name, description) and instructions
  scripts/ references/ assets/
examples/<name>/        sample input and output for each skill (not installed)
tests/                  stdlib unit tests for the skill scripts
tools/validate.py       checks names, manifests, README install lines, shared files and prose
.claude-plugin/         Claude Code plugin marketplace, one plugin per skill
skills.sh.json          how skills.sh groups these skills on the repo page
install.sh              copy or link skills without npx
```

## Add a skill

1. Create `skills/<name>/SKILL.md`. The frontmatter `name` matches the folder (lowercase, digits,
   single hyphens). The `description` says what the skill does and when to use it, in under 1024
   characters, because agents use it to decide when to load the skill.
2. Add the skill to `.claude-plugin/marketplace.json`, to a group in `skills.sh.json`, and to the
   table and install lines in this README.
3. Run `python3 tools/validate.py` and `python3 -m unittest discover tests`.
4. Commit with a short conventional message, e.g. `feat: <name> skill`.

[PUBLISHING.md](PUBLISHING.md) covers how skills get listed on skills.sh.

## License

MIT © 2026 Sanjai Balajee. See [LICENSE](LICENSE).
