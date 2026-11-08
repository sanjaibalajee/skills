#!/usr/bin/env python3
"""
validate.py: keep the repo installable everywhere when skills are added or changed.

    python3 tools/validate.py          # check everything, exit 1 on any error
    python3 tools/validate.py --sync   # copy blueprint's shared renderer into replay first

Checks
  - every skills/<name>/SKILL.md has frontmatter whose name matches the folder,
    follows the agent-skills naming rules, and has a description under 1024 chars
  - .claude-plugin/marketplace.json and skills.sh.json list every skill, and nothing else
  - README.md has an install line for every skill
  - blueprint and replay carry identical copies of the shared renderer
  - the newer skills' docs and the README pass unslop --strict
"""
import filecmp
import importlib.util
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
NAME_RX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHARED = ["scripts/build.py", "scripts/template.html", "references/BLOCKS.md"]
UNSLOP_STRICT = ["README.md", "PUBLISHING.md", "skills/unslop/SKILL.md", "skills/plan-doc/SKILL.md",
                 "skills/plan-doc/references/components.md"]

errors = []


def err(msg):
    errors.append(msg)


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).split("\n"):
        kv = re.match(r"([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            fm[kv.group(1)] = kv.group(2).strip()
    return fm


def skill_names():
    return sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def check_skills(names):
    for n in names:
        fm = frontmatter(os.path.join(SKILLS, n, "SKILL.md"))
        if fm is None:
            err("%s: SKILL.md has no frontmatter" % n)
            continue
        if fm.get("name") != n:
            err("%s: frontmatter name %r must match the folder" % (n, fm.get("name")))
        if not NAME_RX.match(n) or len(n) > 64:
            err("%s: names are lowercase letters, digits and single hyphens, max 64" % n)
        desc = fm.get("description", "")
        if not desc:
            err("%s: description is required" % n)
        elif len(desc) > 1024:
            err("%s: description is %d chars (max 1024)" % (n, len(desc)))
        if re.search(r"[<>]", desc):
            err("%s: description must not contain < or >" % n)


def check_manifests(names):
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
        market = json.load(f)
    listed = []
    for p in market.get("plugins", []):
        for s in p.get("skills", []):
            listed.append(os.path.basename(s.rstrip("/")))
            if not os.path.isfile(os.path.join(ROOT, s, "SKILL.md")):
                err("marketplace.json: %s has no SKILL.md" % s)
    if sorted(listed) != names:
        err("marketplace.json lists %s, skills/ has %s" % (sorted(listed), names))

    with open(os.path.join(ROOT, "skills.sh.json"), encoding="utf-8") as f:
        groups = json.load(f).get("groupings", [])
    grouped = sorted(s for g in groups for s in g.get("skills", []))
    if grouped != names:
        err("skills.sh.json groups %s, skills/ has %s" % (grouped, names))

    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    for n in names:
        if "--skill %s" % n not in readme:
            err("README.md: no `npx skills add ... --skill %s` line" % n)


def check_shared(sync):
    a, b = os.path.join(SKILLS, "blueprint"), os.path.join(SKILLS, "replay")
    for rel in SHARED:
        src, dst = os.path.join(a, rel), os.path.join(b, rel)
        if sync:
            shutil.copyfile(src, dst)
        elif not filecmp.cmp(src, dst, shallow=False):
            err("%s differs between blueprint and replay (run tools/validate.py --sync)" % rel)


def check_prose():
    path = os.path.join(SKILLS, "unslop", "scripts", "scan.py")
    spec = importlib.util.spec_from_file_location("scan", path)
    scan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan)
    rules = scan.compile_rules([])
    for rel in UNSLOP_STRICT:
        full = os.path.join(ROOT, rel)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8") as f:
            found, _ = scan.scan_lines(scan.prose_lines(f.read()), rules, set())
        for x in found:
            if x["severity"] in ("high", "medium"):
                err("%s:%d unslop %s %r" % (rel, x["line"], x["rule"], x["match"]))


def main():
    sync = "--sync" in sys.argv[1:]
    names = skill_names()
    check_skills(names)
    check_manifests(names)
    check_shared(sync)
    check_prose()
    for e in errors:
        print("error  " + e)
    print("%d skills (%s): %s" % (len(names), ", ".join(names), "ok" if not errors else "%d errors" % len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
