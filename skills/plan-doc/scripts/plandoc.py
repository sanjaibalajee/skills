#!/usr/bin/env python3
"""
plandoc.py: scaffold, check and export plan-doc HTML files.

    python3 plandoc.py new "Webhook retries" [--out plans/] [--status draft] [--author NAME]
    python3 plandoc.py check plans/webhook-retries.html
    python3 plandoc.py fragment plans/webhook-retries.html [-o out.html]

new       copies assets/template.html, fills title, date, author, repo and branch
          (read from .git files and ~/.gitconfig), and prints the new path.
check     lints a doc: leftover placeholders, title shape, required sections,
          theme tokens, stray color literals, external hosts, em dashes. If the
          unslop skill is installed next to this one, its scanner runs too.
fragment  writes a copy without the <!doctype>/<html>/<head>/<body> wrapper, for
          hosts (like claude.ai Artifacts) that wrap pages in their own skeleton.

Stdlib only. No network, no subprocesses.
"""
import argparse
import datetime
import html
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
TEMPLATE = os.path.join(SKILL_DIR, "assets", "template.html")
STATUSES = {"draft": "draft", "in-review": "in review", "approved": "approved",
            "in-progress": "in progress", "done": "done", "dropped": "dropped"}
REQUIRED = ["recommendation", "outcome", "changes", "steps", "questions"]
ALLOWED_HOSTS = ("cdn.jsdelivr.net/npm/", "cdnjs.cloudflare.com", "unpkg.com",
                 "fonts.googleapis.com", "fonts.gstatic.com")
GENERIC_TITLES = {"plan", "plan doc", "design doc", "proposal", "rfc", "project plan", "document",
                  "untitled", "new plan", "implementation plan", "technical plan"}


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


# --------------------------------------------------------------------------
# new
# --------------------------------------------------------------------------

def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60].rstrip("-") or "plan"


def find_git_dir(start):
    d = os.path.abspath(start)
    while True:
        g = os.path.join(d, ".git")
        if os.path.isdir(g):
            return g
        if os.path.isfile(g):  # worktree: "gitdir: <path>"
            m = re.match(r"gitdir:\s*(.+)", read_text(g).strip())
            if m:
                return os.path.normpath(os.path.join(d, m.group(1)))
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def git_info(start):
    """(repo, branch, author) from plain files; any of them may be ''."""
    repo = branch = author = ""
    g = find_git_dir(start)
    if g:
        head = os.path.join(g, "HEAD")
        if os.path.isfile(head):
            m = re.match(r"ref: refs/heads/(.+)", read_text(head).strip())
            branch = m.group(1) if m else ""
        cfg_dir = g
        common = os.path.join(g, "commondir")
        if os.path.isfile(common):
            cfg_dir = os.path.normpath(os.path.join(g, read_text(common).strip()))
        cfg = os.path.join(cfg_dir, "config")
        if os.path.isfile(cfg):
            text = read_text(cfg)
            m = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', text)
            if m:  # git@github.com:owner/repo.git or https://host/owner/repo
                parts = re.split(r"[:/]", re.sub(r"\.git$", "", m.group(1).rstrip("/")))
                repo = "/".join(parts[-2:])
            m = re.search(r"\[user\][^\[]*?name\s*=\s*(.+)", text)
            author = m.group(1).strip() if m else ""
        if not repo:
            repo = os.path.basename(os.path.dirname(g)) if os.path.basename(g) == ".git" else ""
    if not author:
        gc = os.path.expanduser("~/.gitconfig")
        if os.path.isfile(gc):
            m = re.search(r"\[user\][^\[]*?name\s*=\s*(.+)", read_text(gc))
            author = m.group(1).strip() if m else ""
    return repo, branch, author


def cmd_new(a):
    title = a.title.strip()
    if not title:
        sys.exit("plandoc: title is required")
    if a.status not in STATUSES:
        sys.exit("plandoc: status must be one of: " + ", ".join(STATUSES))
    repo, branch, author = git_info(os.getcwd())
    author = a.author or author or "unknown"
    where = repo + ("@" + branch if branch and repo else branch)
    out_dir = a.out
    path = a.out if a.out.endswith(".html") else os.path.join(out_dir, slugify(title) + ".html")
    if os.path.exists(path) and not a.force:
        sys.exit("plandoc: %s exists (use --force to overwrite)" % path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    text = read_text(TEMPLATE)
    fill = {"title": html.escape(title), "date": datetime.date.today().isoformat(),
            "author": html.escape(author), "repo": html.escape(where),
            "status": a.status, "status_label": STATUSES[a.status]}
    for k, v in fill.items():
        text = text.replace("{{%s}}" % k, v)
    if not where:
        text = text.replace("    <span></span>\n", "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(os.path.abspath(path))


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------

def css_rules(css):
    """Innermost `selector { body }` pairs, good enough for a lint."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.findall(r"([^{}]+)\{([^{}]*)\}", css)


def visible_text(doc):
    t = re.sub(r"<(script|style|pre|code|svg)\b.*?</\1\s*>", " ", doc, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t)


def load_unslop():
    p = os.path.join(os.path.dirname(SKILL_DIR), "unslop", "scripts", "scan.py")
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location("unslop_scan", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_check(a):
    doc = read_text(a.file)
    errors, warns = [], []

    for m in re.finditer(r"\[\[.*?\]\]|\{\{\w+\}\}", doc):
        line = doc.count("\n", 0, m.start()) + 1
        errors.append("line %d: unfilled placeholder %s" % (line, m.group(0)[:50]))
    if re.search(r"lorem ipsum", doc, re.I):
        errors.append("lorem ipsum left in the doc")

    m = re.search(r"<title>(.*?)</title>", doc[:8192], re.S | re.I)
    title = html.unescape(m.group(1)).strip() if m else ""
    if not title:
        errors.append("no <title> in the first 8 KB")
    else:
        words = len(title.split())
        if re.search(r"\s[-:|–—]\s|:\s", title):
            warns.append("title %r explains itself; keep the name, move the rest to the lede" % title)
        if title.lower() in GENERIC_TITLES:
            errors.append("title %r is a category, not a name" % title)
        if words > 7:
            warns.append("title has %d words; aim for two to five" % words)

    if len(re.findall(r"<h1\b", doc, re.I)) != 1:
        warns.append("expected exactly one <h1>")
    for sid in REQUIRED:
        if not re.search(r'<section\b[^>]*\bid="%s"' % sid, doc):
            warns.append('missing required section id="%s"' % sid)
    if not re.search(r"<li\b", doc[doc.find('id="questions"'):] if 'id="questions"' in doc else ""):
        warns.append("open questions section has no items; delete it or add the questions")

    style = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", doc, re.S | re.I))
    if not re.search(r"(?m)^\s*:root\s*\{", style):
        errors.append("no :root token block")
    if ':root:not([data-theme="light"])' not in style or ':root[data-theme="dark"]' not in style:
        warns.append("dark theme needs both the guarded media block and :root[data-theme=\"dark\"]")
    if not re.search(r"body\s*\{[^}]*background\s*:", style):
        errors.append("body has no explicit background")
    for sel, body in css_rules(style):
        if ":root" in sel:
            continue
        lit = re.search(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(", body)
        if lit:
            warns.append("color literal in %r; use a token" % sel.strip()[:40])
    if re.search(r"\b(?:linear|radial|conic)-gradient\(", style):
        warns.append("gradient found; the house style has none")
    if re.search(r"box-shadow\s*:\s*(?!none)", style):
        warns.append("box-shadow found; use a hairline instead")

    for m in re.finditer(r"""<(?:script|link|img|iframe)\b[^>]*?(?:src|href)\s*=\s*["'](?:https?:)?//([^"']+)""",
                         doc, re.I):
        if not any(m.group(1).startswith(h) for h in ALLOWED_HOSTS):
            warns.append("external resource %s will not load in a sandboxed viewer" % m.group(1)[:60])
    for m in re.finditer(r"""src\s*=\s*["']https?://cdn\.jsdelivr\.net/npm/([^"'/]+)/""", doc):
        if not re.search(r"@\d+\.\d+\.\d+", m.group(1)):
            warns.append("pin %s to an exact version" % m.group(1))

    text = visible_text(doc)
    dashes = text.count("—")
    if dashes:
        warns.append("%d em dash%s in visible text (house rule: none)" % (dashes, "es" if dashes > 1 else ""))
    size = len(doc.encode("utf-8"))
    if size > 2_000_000:
        warns.append("doc is %.1f MB; inline less" % (size / 1e6))

    scan = None if a.no_unslop else load_unslop()
    if scan:
        lines = scan.html_lines(doc)
        found, words = scan.scan_lines(lines, scan.compile_rules([]), set(), scan.html_headings(doc), "html")
        found = [f for f in found if f["severity"] != "low" and f["rule"] != "em-dash"]
        for f in found[:25]:
            warns.append("line %d: unslop %s %r -> %s" % (f["line"], f["rule"], f["match"], f["hint"]))
        if len(found) > 25:
            warns.append("... %d more unslop findings" % (len(found) - 25))

    for e in errors:
        print("error  " + e)
    for w in warns:
        print("warn   " + w)
    print("%s: %d errors, %d warnings%s" % (a.file, len(errors), len(warns),
                                           "" if scan or a.no_unslop else " (unslop not installed; prose not scanned)"))
    return 1 if errors else 0


# --------------------------------------------------------------------------
# fragment
# --------------------------------------------------------------------------

def cmd_fragment(a):
    doc = read_text(a.file)
    head = re.search(r"<head\b[^>]*>(.*?)</head>", doc, re.S | re.I)
    body = re.search(r"<body\b[^>]*>(.*?)</body>", doc, re.S | re.I)
    if not head or not body:
        sys.exit("plandoc: %s has no <head>/<body>; it may already be a fragment" % a.file)
    h = head.group(1)
    h = re.sub(r'<meta\s+charset[^>]*>\s*', "", h, flags=re.I)
    h = re.sub(r'<meta\s+name="viewport"[^>]*>\s*', "", h, flags=re.I)
    b = body.group(1)
    # Artifact viewers render <pre class="mermaid"> natively; drop the CDN loader.
    b = re.sub(r'<script\s+src="[^"]*mermaid[^"]*"\s*>\s*</script>\s*', "", b, flags=re.I)
    b = re.sub(r"<script>\s*window\.mermaid.*?</script>\s*", "", b, flags=re.S | re.I)
    out = h.strip() + "\n" + b.strip() + "\n"
    dest = a.output or re.sub(r"\.html?$", "", a.file) + ".artifact.html"
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    print(os.path.abspath(dest))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scaffold, check and export plan-doc HTML files.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="create a doc from the template")
    n.add_argument("title")
    n.add_argument("--out", default="plans", help="directory, or a .html path (default: plans/)")
    n.add_argument("--status", default="draft", help="|".join(STATUSES))
    n.add_argument("--author", help="defaults to git user.name")
    n.add_argument("--force", action="store_true", help="overwrite an existing file")
    c = sub.add_parser("check", help="lint a doc")
    c.add_argument("file")
    c.add_argument("--no-unslop", action="store_true", help="skip the prose scan")
    f = sub.add_parser("fragment", help="write a skeleton-free copy for artifact hosts")
    f.add_argument("file")
    f.add_argument("-o", "--output")
    a = ap.parse_args(argv)
    return {"new": cmd_new, "check": cmd_check, "fragment": cmd_fragment}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
