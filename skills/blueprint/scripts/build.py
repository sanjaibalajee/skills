#!/usr/bin/env python3
"""
build.py — compile a structured artifact model (JSON) into ONE self-contained
HTML file for the visual-plan / visual-recap skills.

The model JSON is embedded verbatim inside the HTML as the source of truth, so
the output file is at once: a human-viewable document, a machine-readable model
(the agent can re-read it), and a portable offline artifact. No network needed
to view it; no build step at view time.

Usage:
    python3 build.py model.json -o plan.html
    python3 build.py model.json -o plan.html --mermaid vendor/mermaid.min.js
    python3 build.py model.json -o plan.html --fetch-mermaid   # downloads + caches once
    cat model.json | python3 build.py - -o plan.html

Stdlib only. Works offline (except --fetch-mermaid, which needs network once).
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
VENDOR_DIR = os.path.join(HERE, "vendor")
MERMAID_CACHE = os.path.join(VENDOR_DIR, "mermaid.min.js")
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"


def load_model(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"error: model is not valid JSON ({e})")


def validate(model):
    """Cheap sanity checks so a malformed model fails loudly, not silently."""
    warns = []
    if not isinstance(model, dict):
        sys.exit("error: model must be a JSON object")
    if not model.get("title"):
        warns.append("missing 'title'")
    if model.get("kind") not in ("plan", "recap", None):
        warns.append(f"unusual 'kind': {model.get('kind')!r} (expected 'plan' or 'recap')")
    blocks = model.get("blocks", [])
    if not isinstance(blocks, list):
        sys.exit("error: 'blocks' must be an array")
    KNOWN = {"heading", "prose", "callout", "metrics", "steps", "checklist",
             "diagram", "filetree", "diff", "code", "datamodel", "api",
             "decision", "risk", "drift", "wireframe", "questions", "tabs", "divider"}
    for i, b in enumerate(blocks):
        if not isinstance(b, dict) or "type" not in b:
            sys.exit(f"error: block[{i}] must be an object with a 'type'")
        if b["type"] not in KNOWN:
            warns.append(f"block[{i}] unknown type {b['type']!r}")
    for w in warns:
        print(f"  warn: {w}", file=sys.stderr)
    return len(blocks)


def _tabs_have_diagrams(model):
    for b in model.get("blocks", []):
        if b.get("type") == "tabs":
            for t in b.get("tabs", []):
                if any(x.get("type") == "diagram" for x in t.get("blocks", [])):
                    return True
    return False


def fetch_mermaid():
    import urllib.request
    os.makedirs(VENDOR_DIR, exist_ok=True)
    print(f"  fetching mermaid → {MERMAID_CACHE}", file=sys.stderr)
    with urllib.request.urlopen(MERMAID_URL, timeout=60) as r:
        data = r.read().decode("utf-8")
    open(MERMAID_CACHE, "w", encoding="utf-8").write(data)
    return data


def main():
    ap = argparse.ArgumentParser(description="Compile an artifact model into one self-contained HTML file.")
    ap.add_argument("model", help="path to model JSON, or - for stdin")
    ap.add_argument("-o", "--out", required=True, help="output .html path")
    ap.add_argument("--template", default=TEMPLATE, help="renderer template (default: bundled)")
    ap.add_argument("--mermaid", help="path to a vendored mermaid.min.js to inline (offline diagrams)")
    ap.add_argument("--fetch-mermaid", action="store_true", help="download + cache mermaid once, then inline it")
    args = ap.parse_args()

    model = load_model(args.model)
    n = validate(model)

    tpl = open(args.template, encoding="utf-8").read()

    # source of truth, embedded. escape only the </script> sequence so the
    # JSON cannot terminate its host <script> tag.
    data_json = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")

    # Only inline the (large) mermaid lib when the model actually has diagrams,
    # so diagram-free artifacts stay tiny.
    has_diagrams = any(b.get("type") == "diagram" for b in model.get("blocks", [])) or _tabs_have_diagrams(model)
    mermaid_js = ""
    src = args.mermaid
    if has_diagrams:
        if args.fetch_mermaid and not src:
            try:
                mermaid_js = fetch_mermaid()
            except Exception as e:
                print(f"  warn: mermaid fetch failed ({e}); diagrams will show as source", file=sys.stderr)
        elif not src and os.path.exists(MERMAID_CACHE):
            src = MERMAID_CACHE  # reuse cached lib if present
        if src and not mermaid_js:
            mermaid_js = open(src, encoding="utf-8").read()
        if not mermaid_js:
            print("  note: diagrams present but mermaid not inlined — pass --fetch-mermaid "
                  "for offline rendering (shown as source otherwise)", file=sys.stderr)

    html = (tpl
            .replace("__TITLE__", str(model.get("title", "Artifact")))
            .replace("__ARTIFACT_DATA__", data_json)
            .replace("__VENDOR_MERMAID__", mermaid_js))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    open(args.out, "w", encoding="utf-8").write(html)
    kb = len(html.encode("utf-8")) / 1024
    diag = "inlined (offline)" if mermaid_js else "source-fallback"
    print(f"✓ {args.out}  ·  {n} blocks  ·  {kb:.0f} KB  ·  mermaid: {diag}", file=sys.stderr)


if __name__ == "__main__":
    main()
