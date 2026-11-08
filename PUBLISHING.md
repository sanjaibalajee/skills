# Publishing on skills.sh

skills.sh has no submission form and no approval step. A repo gets listed when people install from it
with the `skills` CLI, and installs decide its rank. This is how that works for this repo, based on the
[skills.sh docs](https://skills.sh/docs), [FAQ](https://skills.sh/docs/faq) and
[CLI repo](https://github.com/vercel-labs/skills).

## How a skill gets listed

1. The repo is public on GitHub and its skills sit where the CLI looks (`skills/<name>/SKILL.md`).
   This repo already does both.
2. Someone runs `npx skills add sanjaibalajee/skills ...` with telemetry on, which is the default. The
   CLI sends an anonymous install event, and that event creates the listing.
3. The leaderboard ranks skills by install count. Nothing else feeds it.

So the first listing happens the first time anyone, including you, installs a skill from the repo:

```bash
npx skills add sanjaibalajee/skills --skill unslop -g -a claude-code
```

Installs with `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` set don't count. The pages will be
`skills.sh/sanjaibalajee/skills` for the repo and `skills.sh/sanjaibalajee/skills/<skill>` for each skill.

## What there is to "approve"

- **No review gate.** The FAQ describes no submission, review or minimum install count.
- **Security audits run anyway.** skills.sh shows audit results from Gen Agent Trust Hub, Socket and
  Snyk on each skill (Safe, Low Risk, Med Risk, High Risk, or Pending). They don't publish the rubric.
  What keeps this repo's results clean:
  - `unslop/scripts/scan.py` and `plan-doc/scripts/plandoc.py` are stdlib Python with no network calls
    and no subprocesses.
  - The only network call in the repo is blueprint and replay's opt-in `--fetch-mermaid`, which
    downloads one pinned Mermaid build from jsDelivr.
  - No `curl | sh` install steps, no obfuscated code, no credentials, no instructions that tell an
    agent to bypass the user.
- **The Official section** exists, but skills.sh doesn't say how a skill gets in, and there's no form
  to apply.

## The repo page

`skills.sh.json` at the repo root groups the skills into sections on the repo page (Writing,
Planning, Review). It only changes the display. Changes show up after the next telemetry-enabled
install, and cached pages can lag.

Add the install-count badge to the README once the listing exists:

```markdown
[![skills.sh](https://skills.sh/b/sanjaibalajee/skills)](https://skills.sh/sanjaibalajee/skills)
```

## Before you announce a release

```bash
python3 tools/validate.py                                  # names, manifests, README lines, prose
python3 -m unittest discover tests                         # script tests
DISABLE_TELEMETRY=1 npx skills add sanjaibalajee/skills --list   # the CLI sees all four skills
git tag v1.1.0 && git push --tags                          # lets people pin a version
```

People can then pin it with `npx skills add sanjaibalajee/skills@v1.1.0 --skill unslop`, and
`npx skills update` moves them forward.

## Claude Code plugin marketplace

`.claude-plugin/marketplace.json` makes the repo a plugin marketplace too. It needs no approval
either: anyone can install with `/plugin install unslop --marketplace sanjaibalajee/skills`. Run
`claude plugin validate .` after editing the manifest.

## Taking something down

skills.sh doesn't document a takedown flow. Its FAQ points problems with a skill to that skill's
GitHub repo. Deleting a skill folder stops new installs of it, but an existing listing may stay up.
