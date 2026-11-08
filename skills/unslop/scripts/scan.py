#!/usr/bin/env python3
"""
scan.py: flag AI-writing tells in prose, with file:line:col and a fix hint.

It reads Markdown or plain text, HTML, git commit messages, and unified diffs.
Code is skipped (fenced blocks, inline code, <pre>, <code>, <script>, <style>),
as are URLs and front matter, so only the words a person reads get judged.

    python3 scan.py README.md docs/*.md
    python3 scan.py plan.html
    pbpaste | python3 scan.py -
    python3 scan.py --commit-msg .git/COMMIT_EDITMSG --strict
    git diff main | python3 scan.py --diff -
    python3 scan.py --format json notes.md

Suppress a line with `unslop:ignore` anywhere on it, or a region with
`unslop:off` ... `unslop:on` (in an HTML comment for Markdown/HTML).

Exit status: 0 ran fine; 1 with --strict when a high-severity tell is found
or the score passes --max-score; 2 usage error.

Stdlib only. No network, no subprocesses.
"""
import argparse
import html
import json
import os
import re
import sys

SEVERITY_WEIGHT = {"high": 3.0, "medium": 1.0, "low": 0.25}
PROSE_EXT = {".md", ".mdx", ".markdown", ".txt", ".rst", ".adoc", ""}
HTML_EXT = {".html", ".htm"}
SCISSORS = "# ------------------------ >8 ------------------------"


# --------------------------------------------------------------------------
# Rules. Each is (id, severity, regex, hint). Regexes are case-insensitive.
# Keep ids stable: config files and references/patterns.md key on them.
# --------------------------------------------------------------------------

def _words(*ws):
    return r"\b(?:" + "|".join(ws) + r")\b"


RULES = [
    # --- high: almost never survives a human edit -------------------------
    ("ai-attribution", "high",
     r"co-authored-by:\s*claude|generated (?:with|by) \[?(?:claude|chatgpt|gpt-?\d|copilot|an ai)"
     r"|\U0001F916\s*generated|claude-session:",
     "drop AI attribution; the work ships under the author's name"),
    ("chatbot-opener", "high",
     r"^\s*(?:certainly|absolutely|sure thing|great question|excellent question|good question"
     r"|happy to help|of course)\s*[!.,]",
     "start with the answer"),
    ("sycophancy", "high",
     r"\byou(?:'re|\u2019re| are) (?:absolutely|totally|completely|so) right\b"
     r"|\b(?:great|excellent|fantastic|brilliant|wonderful) (?:catch|point|idea|question|observation)\b"
     r"|\bwhat a (?:great|fantastic|wonderful|brilliant)\b",
     "cut the praise; respond to the substance"),
    ("chatbot-closer", "high",
     r"\b(?:i )?hope (?:this|that) helps\b|\blet me know if (?:you|there|anything)\b"
     r"|\bfeel free to (?:reach out|ask|let me know|share)\b|\bdon(?:'|\u2019)?t hesitate to\b"
     r"|\bhappy (?:coding|hacking|building)\b|\bif you have any (?:other |further |more )?questions\b",
     "end on the last useful sentence"),
    ("ai-disclaimer", "high",
     r"\bas an ai\b|\bas a (?:large )?language model\b|\bmy (?:knowledge|training) (?:cutoff|data)\b"
     r"|\bi (?:don(?:'|\u2019)?t|do not) have (?:access to )?real-time\b",
     "delete; state the limit plainly if it matters"),
    ("ai-vocab", "high",
     _words(r"delv(?:e|es|ed|ing)", r"tapestr(?:y|ies)", r"testament to", r"in the realm of",
            r"ever-(?:evolving|changing|growing)", r"embark(?:s|ed|ing)? on",
            r"unleash(?:es|ed|ing)?", r"unlock(?:s|ed|ing)? the (?:full )?(?:power|potential)",
            r"game[- ]chang(?:er|ers|ing)", r"a myriad of", r"beacon of", r"symphony of",
            r"navigat(?:e|es|ing) the (?:complexities|intricacies|landscape|world) of",
            r"plays? an? (?:crucial|pivotal|vital|key|significant|central) role",
            r"in today(?:'|\u2019)?s [\w -]{0,24}?(?:world|landscape|era|age|climate)",
            r"intricate (?:dance|interplay|web)", r"rich (?:tapestry|heritage)"),
     "say the plain thing; name what actually happens"),

    ("em-dash", "high",
     r"\u2014|(?<=\w) -- (?=\w)|(?<=\w)\u2013(?=\s)|(?<=\s)\u2013(?=\s)",
     "no em dashes: end the sentence, or use a comma or parentheses"),

    # --- medium: usually filler, sometimes earned -------------------------
    ("hype", "medium",
     r"\b(?:(?:super |so |really )?(?:excited|thrilled|stoked|proud|delighted) to (?:announce|share|introduce|launch|unveil))\b"
     r"|\bmind-?blowing\b|\binsanely\b|\bnext[- ]level\b",
     "state what shipped and let it stand"),
    ("cute-line", "medium",
     r"\band that(?:'|\u2019)?s (?:the (?:whole )?)?(?:point|trick|secret|magic|beauty)\b|\bthat(?:'|\u2019)?s it\. that(?:'|\u2019)?s the\b"
     r"|\bsimple as that\b|\bturns out,|\bhere(?:'|\u2019)?s the (?:twist|catch)\b|\bspoiler:|^\s*less \w+, more \w+\.?\s*$"
     r"|\bwhat could go wrong\b",
     "cut the flourish; end on the fact"),
    ("buzzword", "medium",
     _words(r"seamless(?:ly)?", r"robust(?:ness)?", r"leverag(?:e|es|ed|ing)", r"utiliz(?:e|es|ed|ing|ation)",
            r"comprehensive", r"cutting[- ]edge", r"state[- ]of[- ]the[- ]art", r"best[- ]in[- ]class",
            r"world[- ]class", r"next[- ]gen(?:eration)?", r"elevat(?:e|es|ed|ing)", r"empower(?:s|ed|ing)?",
            r"streamlin(?:e|es|ed|ing)", r"holistic", r"synerg(?:y|ies|istic)", r"revolutioniz(?:e|es|ed|ing)",
            r"supercharg(?:e|es|ed|ing)", r"effortless(?:ly)?", r"blazing(?:ly)?[- ]fast", r"lightning[- ]fast",
            r"enterprise[- ]grade", r"battle[- ]tested", r"transformative", r"groundbreaking",
            r"unparalleled", r"meticulous(?:ly)?", r"foster(?:s|ed|ing)?", r"bolster(?:s|ed|ing)?",
            r"underscor(?:e|es|ed|ing)", r"showcas(?:e|es|ed|ing)", r"garner(?:s|ed|ing)?",
            r"pivotal", r"paramount", r"vibrant", r"bustling", r"nestled"),
     "use the plain word, or the number that proves it"),
    ("corporate-idiom", "medium",
     _words(r"going forward", r"moving forward", r"at the end of the day", r"low[- ]hanging fruit",
            r"move the needle", r"circle back", r"double[- ]click on", r"deep[- ]dive", r"north star",
            r"paradigm shift", r"touch base", r"take (?:it|this|things) to the next level",
            r"best of both worlds", r"at its core", r"the heart of", r"a perfect blend"),
     "say it literally"),
    ("filler-phrase", "medium",
     _words(r"in order to", r"due to the fact that", r"at this point in time", r"for all intents and purposes",
            r"each and every", r"first and foremost", r"it goes without saying", r"needless to say",
            r"in the event that", r"when it comes to", r"a (?:wide|broad|diverse) (?:range|variety|array) of",
            r"with (?:regard|respect) to", r"is able to", r"are able to", r"has the ability to",
            r"the fact that"),
     "shorten: 'in order to' -> 'to', 'is able to' -> 'can', 'in the event that' -> 'if'"),
    ("importance-flag", "medium",
     r"\bit(?:'|\u2019)?s (?:important|crucial|essential|worth) (?:to note|noting|mentioning|remembering|pointing out)\b"
     r"|\bit (?:is|should be) (?:important to note|worth noting|noted)\b|\bkeep in mind that\b"
     r"|^\s*(?:notably|importantly|crucially|interestingly),",
     "delete the announcement; say the thing"),
    ("signposting", "medium",
     r"\blet(?:'|\u2019)?s (?:dive|jump|delve|unpack|break (?:it|this|that) down|explore|take a (?:closer )?look)\b"
     r"|\bhere(?:'|\u2019)?s (?:the thing|the kicker|the deal|what you need to know|a (?:quick )?breakdown)\b"
     r"|\bwithout further ado\b|\bbuckle up\b|\bi want to (?:talk|write) about\b"
     r"|\blet me (?:explain|walk you through|be clear)\b|\bthis (?:post|piece|essay) is (?:about|my attempt)\b"
     r"|\bin this (?:article|post|guide|blog post|document|section|readme),? (?:we|i)(?:'ll| will)\b",
     "skip the preamble and start"),
    ("not-x-but-y", "medium",
     r"\bnot (?:just|only|merely|simply) (?:a |an |the )?\w[^.;:!?\n]{0,60}?,? but\b"
     r"|\b(?:isn(?:'|\u2019)?t|aren(?:'|\u2019)?t|it(?:'|\u2019)?s not|this is not|that(?:'|\u2019)?s not) (?:just|only|merely|simply|about)\b"
     r"|\bmore than just\b",
     "state the positive claim directly"),
    ("fancy-copula", "medium",
     r"\b(?:serves|served|serving) as (?:a|an|the|our)\b|\bstands as (?:a|an|the)\b|\bboasts\b",
     "use 'is' or 'has'"),
    ("ing-tail", "medium",
     r",\s+(?:ensuring|highlighting|showcasing|reflecting|underscoring|emphasizing|fostering|cementing"
     r"|solidifying|paving the way|contributing to|demonstrating|signaling|marking|making it)\b",
     "end the sentence; if the effect matters, give it its own sentence with a subject"),
    ("vague-authority", "medium",
     r"\b(?:experts|studies|research|reports|critics|observers|many (?:people|developers|users|teams))"
     r" (?:say|says|agree|suggest|suggests|show|shows|believe|argue|note)\b"
     r"|\bit is (?:widely|generally|commonly) (?:known|believed|accepted|agreed)\b",
     "name the source, or cut the claim"),
    ("generic-ending", "medium",
     r"^\s*(?:in conclusion|in summary|to sum (?:it )?up|to summarize|all in all|overall|ultimately|in the end)[,:]"
     r"|\bthe future (?:looks|is) bright\b|\bexciting times ahead\b|\bonly time will tell\b"
     r"|\bthe possibilities are (?:endless|limitless)\b|\bthe sky(?:'|\u2019)?s the limit\b",
     "end on a specific fact, next step, or nothing"),
    ("self-narration", "medium",
     r"\bthis (?:commit|pr|pull request|change|changeset|patch|update|readme|guide)"
     r" (?:introduces|adds|implements|aims to|is designed to|provides|addresses|enhances|delivers)\b"
     r"|\bin this (?:commit|pr|pull request)\b",
     "lead with the change itself: 'Adds X' or just 'X'"),
    ("meta-reply", "medium",
     r"^\s*here(?:'|\u2019)?s (?:the|a|an|your) (?:updated|revised|rewritten|improved|refined|polished|final|complete)\b"
     r"|\bi(?:'|\u2019)?ve (?:gone ahead and|taken the liberty)\b|\bas (?:you )?requested\b",
     "drop the wrapper; give the thing"),
    ("hedge-stack", "medium",
     r"\b(?:may|might|could|can) (?:potentially|possibly|perhaps|conceivably)\b|\bit could be argued\b"
     r"|\barguably\b|\bto some (?:extent|degree)\b|\bin some (?:ways|sense)\b",
     "hedge once, where the doubt is real"),
    ("bold-label-bullet", "medium",
     r"^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*|__)[^*_\n]{1,48}?(?::(?:\*\*|__)|(?:\*\*|__):)",
     "make it a sentence, or a table if the labels repeat"),

    # --- low: fine alone, a tell in bulk ----------------------------------
    ("intensifier", "low",
     _words(r"very", r"really", r"truly", r"incredibly", r"extremely", r"highly", r"deeply", r"remarkably",
            r"significantly", r"dramatically", r"exceptionally", r"literally", r"basically", r"essentially"),
     "cut it, or use the stronger word or the number"),
    ("exclamation", "low", r"(?<![!=\\])!(?![=\[(!])",
     "use a period"),
    ("curly-quotes", "low", r"[\u2018\u2019\u201c\u201d]",
     "straight quotes in technical text"),
]

DICTATION_RULES = [
    ("dictation-filler", "medium",
     r"\b(?:uh+|um+|erm|uhm)\b|,?\s*\byou know\b,?|\bi mean\b,?|\bsort of\b|\bkind of\b|\bbasically\b",
     "drop the filler"),
    ("self-correction", "high",
     r",?\s*\b(?:sorry|no wait|scratch that|or rather|i mean)\s*,",
     "keep only the corrected version of the phrase"),
    ("repeated-word", "medium", r"\b(\w+)(?:,?\s+\1\b)+",
     "dictation stutter; keep one"),
]

EMOJI = (r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF"
         r"\U00002B50\U00002B06\U00002705\U0000274C]")
EMOJI_MARKER = re.compile(r"^\s*(?:#{1,6}\s*|[-*+]\s+|\d+[.)]\s+)?" + EMOJI)
HEADING_MD = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "is", "of",
               "on", "or", "the", "to", "vs", "via", "with"}
ADJ_SUFFIX = re.compile(r"(?:able|ible|ful|less|ive|ous|ent|ant|ic|al|ient)$", re.I)
TRIPLET = re.compile(r"\b([A-Za-z]{4,}), ([A-Za-z]{4,}),? and ([A-Za-z]{4,})\b")
PAST_TENSE_SUBJECT = re.compile(
    r"^(?:\w+(?:\([^)]*\))?!?:\s*)?(?:added|adds|fixed|fixes|updated|updates|removed|removes|changed"
    r"|changes|implemented|implements|refactored|refactors|created|creates)\b", re.I)


def compile_rules(extra, dictation=False):
    out = []
    for rid, sev, pat, hint in RULES + (DICTATION_RULES if dictation else []) + extra:
        flags = re.I | (re.M if pat.startswith("^") else 0)
        out.append((rid, sev, re.compile(pat, flags), hint))
    return out


# --------------------------------------------------------------------------
# Masking: turn a source into a list of (line_no, text) the rules can read.
# Masked spans become spaces so columns stay true wherever possible.
# --------------------------------------------------------------------------

def _blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


INLINE_MASKS = [
    re.compile(r"(`+)(?:(?!\1).)+?\1"),          # inline code
    re.compile(r"<!--.*?-->"),                     # html comments
    re.compile(r"\]\([^)\s]*(?:\s+\"[^\"]*\")?\)"), # link targets
    re.compile(r"<https?://[^>]+>|https?://\S+"),  # urls
    re.compile(r"</?[A-Za-z][^>\n]*>"),            # inline html tags
]


def mask_inline(line):
    for rx in INLINE_MASKS:
        line = rx.sub(_blank, line)
    return line


def mask_regions(text):
    """Blank `unslop:off` ... `unslop:on` regions, keeping line breaks."""
    return re.sub(r"[^\n]*unslop:off.*?(?:unslop:on[^\n]*|\Z)", _blank, text, flags=re.S)


def prose_lines(text):
    """Markdown/plain text -> [(line_no, masked_line)], skipping code and front matter."""
    lines = mask_regions(text).split("\n")
    out, fence, front = [], None, False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if i == 1 and s == "---":
            front = True
            continue
        if front:
            front = s not in ("---", "...")
            continue
        m = re.match(r"\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        if "unslop:ignore" in line or re.match(r"^(?: {4}|\t)(?!\s*(?:[-*+]|\d+[.)])\s)", line):
            continue  # suppressed, or an indented code block
        out.append((i, mask_inline(line)))
    return out


def html_lines(text):
    """HTML -> [(line_no, visible_text_line)]. Columns are approximate after entities decode."""
    t = mask_regions(text)
    for tag in ("script", "style", "pre", "code", "svg", "textarea", "template"):
        t = re.sub(r"<%s\b.*?</%s\s*>" % (tag, tag), _blank, t, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", _blank, t, flags=re.S)
    t = re.sub(r"<[^>]+>", _blank, t, flags=re.S)
    out = []
    for i, line in enumerate(t.split("\n"), 1):
        if "unslop:ignore" in line:
            continue
        out.append((i, html.unescape(line)))
    return out


def html_headings(text):
    """[(line_no, heading_text)] for <h1>-<h6>, so the title-case check works on HTML too."""
    t = mask_regions(text)
    found = []
    for m in re.finditer(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]\s*>", t, flags=re.S | re.I):
        inner = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        found.append((t.count("\n", 0, m.start()) + 1, inner))
    return found


def html_bold_labels(text):
    """<li><strong>Label:</strong> ... is the HTML form of a bold-label bullet."""
    t = mask_regions(text)
    rx = re.compile(r"<li\b[^>]*>\s*<(strong|b)\b[^>]*>[^<]{1,48}?:\s*</\1>|<li\b[^>]*>\s*<(strong|b)\b[^>]*>[^<]{1,48}?</\2>:",
                    re.I)
    return [t.count("\n", 0, m.start()) + 1 for m in rx.finditer(t)]


def commit_lines(text):
    """Commit message -> prose lines (comment lines and the scissors tail dropped)."""
    keep = []
    for line in text.split("\n"):
        if line.startswith(SCISSORS):
            break
        keep.append("" if line.startswith("#") else line)
    return prose_lines("\n".join(keep))


COMMENT_LEAD = re.compile(r"^\s*(?://+|#+(?!!)|\*+(?!/)|/\*+|--|;+|<!--)\s?(.*)$")


def diff_sources(text):
    """Unified diff -> {path: [(new_line_no, added_text)]} for added lines only."""
    files, path, ln, in_header = {}, None, 0, False
    for raw in text.split("\n"):
        if raw.startswith("diff --git"):
            path, in_header = None, True
            continue
        if in_header and raw.startswith("+++ "):
            p = raw[4:].strip().split("\t")[0]
            path = None if p == "/dev/null" else re.sub(r"^[ab]/", "", p)
            files.setdefault(path, []) if path else None
            continue
        if in_header and (raw.startswith("--- ") or raw.startswith("index ") or raw.startswith("new file")
                          or raw.startswith("deleted file") or raw.startswith("similarity")
                          or raw.startswith("rename ") or raw.startswith("old mode") or raw.startswith("new mode")):
            continue
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            ln, in_header = int(m.group(1)), False
            continue
        if path is None or in_header:
            continue
        if raw.startswith("+"):
            files[path].append((ln, raw[1:]))
            ln += 1
        elif raw.startswith(" ") or raw == "":
            ln += 1
    return files


def diff_lines_for(path, added):
    ext = os.path.splitext(path)[1].lower()
    if ext in PROSE_EXT:
        text_lines = [(n, mask_inline(t)) for n, t in added
                      if "unslop:ignore" not in t and not re.match(r"\s{0,3}(`{3,}|~{3,})", t)]
        return text_lines, "prose"
    if ext in HTML_EXT:
        return [(n, html.unescape(re.sub(r"<[^>]+>", " ", t))) for n, t in added], "html"
    # code: judge comments only
    out = []
    for n, t in added:
        m = COMMENT_LEAD.match(t)
        if m and m.group(1).strip():
            out.append((n, mask_inline(m.group(1))))
    return out, "code"


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------

def is_title_case(text):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\u2019-]*", text)]
    big = [w for w in words if w.lower() not in SMALL_WORDS]
    if len(big) < 3:
        return False
    caps = [w for w in big[1:] if w[0].isupper() and not w.isupper()]
    return len(caps) >= max(2, int(0.8 * (len(big) - 1)))


def scan_lines(lines, rules, allow, headings=None, kind="prose"):
    findings = []
    words = 0
    for n, line in lines:
        words += len(re.findall(r"[A-Za-z0-9][\w'\u2019-]*", line))
        for rid, sev, rx, hint in rules:
            for m in rx.finditer(line):
                hit = m.group(0).strip()
                if hit.lower() in allow:
                    continue
                findings.append({"line": n, "col": m.start() + 1, "rule": rid, "severity": sev,
                                 "match": hit[:60], "hint": hint})
        if EMOJI_MARKER.search(line):
            findings.append({"line": n, "col": 1, "rule": "emoji-marker", "severity": "medium",
                             "match": line.strip()[:40], "hint": "drop decorative emoji from headings and bullets"})
        for m in TRIPLET.finditer(line):
            trio = [g for g in m.groups()]
            if sum(1 for w in trio if ADJ_SUFFIX.search(w) or w.lower().endswith("ly")) >= 2:
                findings.append({"line": n, "col": m.start() + 1, "rule": "rule-of-three", "severity": "low",
                                 "match": m.group(0), "hint": "keep the items that carry weight; two is fine"})
    heads = headings if headings is not None else [
        (n, HEADING_MD.match(l).group(1)) for n, l in lines if kind == "prose" and HEADING_MD.match(l)]
    for n, h in heads:
        if is_title_case(h):
            findings.append({"line": n, "col": 1, "rule": "title-case-heading", "severity": "low",
                             "match": h[:60], "hint": "use sentence case"})
    return findings, words


def commit_checks(text, rules_off):
    """Subject-line checks that only make sense for commit messages."""
    lines = [l for l in text.split("\n") if not l.startswith("#")]
    subj_i = next((i for i, l in enumerate(lines) if l.strip()), None)
    if subj_i is None:
        return []
    subj, n = lines[subj_i].rstrip(), subj_i + 1
    out = []

    def add(rid, sev, hint):
        if rid not in rules_off:
            out.append({"line": n, "col": 1, "rule": rid, "severity": sev, "match": subj[:60], "hint": hint})

    if len(subj) > 72:
        add("commit-subject-length", "medium", "keep the subject under ~72 characters (aim for 50)")
    if subj.endswith("."):
        add("commit-subject-period", "low", "no trailing period on the subject")
    if PAST_TENSE_SUBJECT.match(subj):
        add("commit-subject-mood", "low", "imperative mood: 'add', 'fix', not 'added'/'adds'")
    return out


def score(findings, words):
    pts = sum(SEVERITY_WEIGHT[f["severity"]] for f in findings)
    return round(100.0 * pts / max(words, 1), 2)


def verdict(s):
    return "clean" if s < 1 else "light" if s < 3 else "heavy" if s < 8 else "slop"


# --------------------------------------------------------------------------
# Config and CLI
# --------------------------------------------------------------------------

def find_config(start):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".unslop.json")
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_config(path):
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        sys.exit("unslop: bad config %s (%s)" % (path, e))
    return cfg if isinstance(cfg, dict) else {}


def read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Flag AI-writing tells in prose.")
    ap.add_argument("paths", nargs="*", help="files to scan; '-' reads stdin")
    ap.add_argument("--html", action="store_true", help="treat stdin as HTML")
    ap.add_argument("--commit-msg", metavar="FILE", help="scan a git commit message file")
    ap.add_argument("--diff", action="store_true", help="input is a unified diff; scan added lines only")
    ap.add_argument("--dictation", action="store_true", help="also flag speech fillers and self-corrections")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--min-severity", choices=("low", "medium", "high"), default="low")
    ap.add_argument("--allow", action="append", default=[], help="phrase to accept (repeatable)")
    ap.add_argument("--disable", action="append", default=[], help="rule id to turn off (repeatable)")
    ap.add_argument("--config", help="path to .unslop.json (default: nearest one upward from cwd)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any high-severity tell")
    ap.add_argument("--max-score", type=float, help="with --strict, also fail when score exceeds this")
    ap.add_argument("--summary", action="store_true", help="print only the per-file summary lines")
    a = ap.parse_args(argv)

    if not a.paths and not a.commit_msg:
        if sys.stdin.isatty():
            ap.print_usage(sys.stderr)
            return 2
        a.paths = ["-"]

    cfg = load_config(a.config or find_config(os.getcwd()))
    allow = {w.lower() for w in a.allow + cfg.get("allow", [])}
    off = set(a.disable + cfg.get("disable", []))
    extra = [(r["id"], r.get("severity", "medium"), r["pattern"], r.get("hint", "house rule"))
             for r in cfg.get("rules", []) if "id" in r and "pattern" in r]
    rules = [r for r in compile_rules(extra, a.dictation) if r[0] not in off]
    floor = ("low", "medium", "high").index(a.min_severity)

    # Build (label, lines, headings, kind, extra_findings) jobs.
    jobs = []
    if a.commit_msg:
        text = read(a.commit_msg)
        jobs.append((a.commit_msg, commit_lines(text), None, "prose", commit_checks(text, off)))
    for p in a.paths:
        try:
            text = read(p)
        except OSError as e:
            print("unslop: %s" % e, file=sys.stderr)
            return 2
        if a.diff:
            for path, added in diff_sources(text).items():
                lines, kind = diff_lines_for(path, added)
                jobs.append((path, lines, [], kind, []))
            continue
        ext = os.path.splitext(p)[1].lower()
        if ext in HTML_EXT or (p == "-" and a.html):
            bold = [{"line": n, "col": 1, "rule": "bold-label-bullet", "severity": "medium",
                     "match": "<li><strong>Label:</strong>", "hint": "make it a sentence, or a table"}
                    for n in html_bold_labels(text)] if "bold-label-bullet" not in off else []
            jobs.append((p, html_lines(text), html_headings(text), "html", bold))
        else:
            jobs.append((p, prose_lines(text), None, "prose", []))

    report, failed = [], False
    for label, lines, heads, kind, pre in jobs:
        found, words = scan_lines(lines, rules, allow, heads, kind)
        found = [f for f in pre + found if f["rule"] not in off]
        seen, uniq = set(), []
        for f in sorted(found, key=lambda f: (f["line"], f["col"], f["rule"])):
            key = (f["line"], f["col"], f["rule"])
            if key not in seen:
                seen.add(key)
                uniq.append(f)
        s = score(uniq, words)
        shown = [f for f in uniq if ("low", "medium", "high").index(f["severity"]) >= floor]
        counts = {k: sum(1 for f in uniq if f["severity"] == k) for k in ("high", "medium", "low")}
        report.append({"file": label, "words": words, "score": s, "verdict": verdict(s),
                       "counts": counts, "findings": shown})
        if a.strict and (counts["high"] or (a.max_score is not None and s > a.max_score)):
            failed = True

    if a.format == "json":
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        for r in report:
            if not a.summary:
                for f in r["findings"]:
                    print('%s:%d:%d  %-6s  %-20s "%s"  -> %s' % (
                        r["file"], f["line"], f["col"], f["severity"], f["rule"], f["match"], f["hint"]))
            c = r["counts"]
            print("%s: %d high, %d medium, %d low in %d words; score %.2f per 100 words (%s)" % (
                r["file"], c["high"], c["medium"], c["low"], r["words"], r["score"], r["verdict"]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
