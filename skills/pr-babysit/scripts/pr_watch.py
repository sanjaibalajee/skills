#!/usr/bin/env python3
"""
pr_watch.py: watch one GitHub pull request and print one line per event that needs a look.

    python3 pr_watch.py 123
    python3 pr_watch.py https://github.com/owner/repo/pull/123 --until ready
    python3 pr_watch.py 123 --repo owner/repo --until green --interval 30

Stdout carries only events, one per line, so a monitor (Claude Code's Monitor tool) wakes the agent
once per event. Progress and errors go to stderr. Needs an authenticated `gh` CLI. Uses the REST API,
whose rate limit is separate from the GraphQL one `gh pr` commands use, plus one GraphQL query for
unresolved review threads in `ready` mode.

--until
  green   the required checks passed on the head (every check, when the base requires none)
  ready   green, not behind, no unresolved review threads, and each review bot that reviewed this
          PR before has reviewed the head (or --bot-grace minutes passed). The default.
  any     stop after the first poll that printed an event

Exit codes
  0  the --until condition is met, or the PR merged
  1  needs action: a check failed, a conflict, behind the base (ready), unresolved threads (ready),
     the PR closed, or GitHub stayed unreachable
  2  bad arguments, unknown PR, or another pr_watch already watches this PR
  3  --max-wait ran out with nothing to act on; start it again

Events
  [check-failed] name url          a required check (or any check, when none are required) failed
  [checks-done] sha summary        every check finished on the head
  [comment] who kind: text url     a new comment, review or review comment from someone else
  [pushed] sha by who              someone other than the gh user moved the head
  [behind] / [conflict]            the base moved ahead, or the branch conflicts
  [threads] n                      unresolved review threads block `ready`
  [green] / [ready] / [merged] / [closed] / [timeout] / [unreachable]

Comments from the account `gh` is logged into aren't reported: the agent's own replies come from it.
State lives in ~/.local/state/pr-babysit/ (PR_BABYSIT_STATE_DIR overrides). The first run records what
already exists and reports only what comes after, so a restarted watcher reports what arrived while
none was running.
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time

STATE_DIR = os.path.expanduser(os.environ.get("PR_BABYSIT_STATE_DIR", "~/.local/state/pr-babysit"))
OK = {"success", "neutral", "skipped"}
FAILED = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale", "error"}
# Deploy and CI bots repeat what the checks already say.
QUIET_AUTHORS = {"github-actions[bot]", "vercel[bot]", "netlify[bot]", "cloudflare-workers-and-pages[bot]",
                 "railway-app[bot]", "render[bot]", "changeset-bot[bot]", "codecov[bot]", "dependabot[bot]"}
NO_CHECKS_GRACE = 300  # seconds to wait for a first check before treating a repo as having no CI
THREADS_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) { reviewThreads(first: 100) { nodes { isResolved } } }
  }
}
"""


class GhError(Exception):
    pass


def log(msg):
    print("pr_watch: " + msg, file=sys.stderr, flush=True)


def emit(line):
    print(line, flush=True)


def gh(args):
    try:
        out = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GhError(str(e))
    if out.returncode != 0:
        raise GhError((out.stderr or out.stdout).strip()[:300])
    return json.loads(out.stdout) if out.stdout.strip() else None


def parse_target(pr, repo):
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr)
    if m:
        return m.group(1), int(m.group(2))
    if not pr.isdigit():
        raise ValueError("expected a PR number or URL, got %r" % pr)
    if not repo:
        repo = gh(["repo", "view", "--json", "nameWithOwner"])["nameWithOwner"]
    return repo, int(pr)


def required_checks(repo, base):
    """Check names the base branch requires, from rulesets and classic protection."""
    names = set()
    try:
        for rule in gh(["api", "repos/%s/rules/branches/%s" % (repo, base)]) or []:
            if rule.get("type") == "required_status_checks":
                for c in rule.get("parameters", {}).get("required_status_checks", []):
                    names.add(c.get("context"))
    except GhError:
        pass
    try:
        prot = gh(["api", "repos/%s/branches/%s/protection/required_status_checks" % (repo, base)]) or {}
        names.update(prot.get("contexts", []))
        names.update(c.get("context") for c in prot.get("checks", []))
    except GhError:
        pass  # 404 without protection, 403 without admin rights: gate on every check instead
    return {n for n in names if n}


def snapshot(repo, number, since, prev_sha):
    pr = gh(["api", "repos/%s/pulls/%d" % (repo, number)])
    sha = pr["head"]["sha"]
    checks = {}
    runs = gh(["api", "repos/%s/commits/%s/check-runs?per_page=100" % (repo, sha)]) or {}
    for r in runs.get("check_runs", []):
        state = (r.get("conclusion") or "pending") if r.get("status") == "completed" else "pending"
        checks[r["name"]] = {"state": state, "url": r.get("html_url") or ""}
    status = gh(["api", "repos/%s/commits/%s/status" % (repo, sha)]) or {}
    for s in status.get("statuses", []):
        checks[s["context"]] = {"state": s["state"], "url": s.get("target_url") or ""}

    comments = []
    query = "?per_page=100&since=%s" % since
    for kind, path in (("comment", "issues/%d/comments" % number), ("review comment", "pulls/%d/comments" % number)):
        for c in gh(["api", "repos/%s/%s%s" % (repo, path, query)]) or []:
            comments.append({"id": "%s-%s" % (kind, c["id"]), "who": c["user"]["login"], "kind": kind,
                             "body": c.get("body") or "", "url": c.get("html_url") or ""})
    for r in gh(["api", "repos/%s/pulls/%d/reviews?per_page=100" % (repo, number)]) or []:
        comments.append({"id": "review-%s" % r["id"], "who": r["user"]["login"],
                         "kind": "review " + (r.get("state") or "").lower(), "body": r.get("body") or "",
                         "url": r.get("html_url") or "", "commit": r.get("commit_id")})

    head_author = None
    if prev_sha and prev_sha != sha:
        commit = gh(["api", "repos/%s/commits/%s" % (repo, sha)]) or {}
        head_author = ((commit.get("author") or {}).get("login")
                       or (commit.get("commit", {}).get("author") or {}).get("name"))
    return {"state": pr["state"], "merged": bool(pr.get("merged")), "sha": sha, "base": pr["base"]["ref"],
            "mergeable_state": pr.get("mergeable_state") or "unknown", "checks": checks,
            "comments": comments, "head_author": head_author}


def unresolved_threads(repo, number):
    owner, name = repo.split("/", 1)
    data = gh(["api", "graphql", "-f", "query=" + THREADS_QUERY, "-F", "owner=" + owner,
               "-F", "name=" + name, "-F", "number=%d" % number])
    nodes = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return sum(1 for n in nodes if not n["isResolved"])


def one_line(text, limit=140):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 1] + "..."


def evaluate(snap, state, required, until, me, now, bot_grace=15, threads=0):
    """Compare a snapshot with the saved state. Returns (events, exit code or None) and updates state."""
    events = []
    first = not state.get("initialized")
    if snap["merged"]:
        return ["[merged]"], 0
    if snap["state"] == "closed":
        return ["[closed]"], 1

    if state.get("sha") != snap["sha"]:
        if state.get("sha") and snap.get("head_author") and snap["head_author"] != me:
            events.append("[pushed] %s by %s" % (snap["sha"][:7], snap["head_author"]))
        state["sha"], state["sha_seen_at"], state["green_at"] = snap["sha"], now, None

    seen = set(state.get("seen", []))
    for c in snap["comments"]:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        if first or c["who"] == me or c["who"] in QUIET_AUTHORS:
            continue
        if c["kind"] == "review commented" and not c["body"].strip():
            continue  # the review's inline comments arrive as their own events
        events.append(("[comment] %s %s: %s %s" % (c["who"], c["kind"], one_line(c["body"]), c["url"])).rstrip())
    state["seen"] = sorted(seen)

    checks = snap["checks"]
    gate = {n: c for n, c in checks.items() if not required or n in required}
    reported = set(state.get("failed", []))
    failed = False
    for name in sorted(gate):
        if gate[name]["state"] in FAILED:
            failed = True
            key = "%s:%s" % (snap["sha"], name)
            if key not in reported:
                reported.add(key)
                events.append("[check-failed] %s %s" % (name, gate[name]["url"]))
    state["failed"] = sorted(reported)

    if checks and all(c["state"] != "pending" for c in checks.values()) and state.get("done_sha") != snap["sha"]:
        state["done_sha"] = snap["sha"]
        counts = {"passed": 0, "skipped": 0, "failed": 0}
        for c in checks.values():
            counts["skipped" if c["state"] == "skipped" else "passed" if c["state"] in OK else "failed"] += 1
        events.append("[checks-done] %s %d passed, %d skipped, %d failed"
                      % (snap["sha"][:7], counts["passed"], counts["skipped"], counts["failed"]))

    merge_state = snap["mergeable_state"]
    if merge_state != state.get("mergeable_state") and merge_state in ("behind", "dirty"):
        events.append("[conflict]" if merge_state == "dirty" else "[behind] the base branch moved ahead")
    state["mergeable_state"] = merge_state
    state["initialized"] = True

    if failed or merge_state == "dirty":
        return events, 1
    if required:
        green = all(gate.get(n, {}).get("state") in OK for n in required)
    elif gate:
        green = all(c["state"] in OK for c in gate.values())
    else:
        green = now - state["sha_seen_at"] >= NO_CHECKS_GRACE  # no CI on this repo
    if green and not state.get("green_at"):
        state["green_at"] = now

    if until == "any":
        return events, (0 if events else None)
    if until == "green":
        return (events + ["[green]"], 0) if green else (events, None)
    if not green:
        return events, None
    if merge_state == "behind":
        return events, 1
    if threads:
        return events + ["[threads] %d unresolved" % threads], 1
    bots = {c["who"] for c in snap["comments"] if c["kind"].startswith("review") and c["who"].endswith("[bot]")}
    on_head = {c["who"] for c in snap["comments"] if c.get("commit") == snap["sha"]}
    if bots - on_head and now - state["green_at"] < bot_grace * 60:
        return events, None
    return events + ["[ready]"], 0


def state_path(repo, number):
    return os.path.join(STATE_DIR, "%s-%d.json" % (repo.replace("/", "-"), number))


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def watch(repo, number, a, me):
    path = state_path(repo, number)
    state = load_state(path)
    required = None
    deadline = time.time() + a.max_wait * 60
    interval = max(15, a.interval)
    failures = 0
    log("watching %s#%d until %s" % (repo, number, a.until))
    while True:
        poll_started = time.time()
        since = state.get("since") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(poll_started - 3600))
        try:
            snap = snapshot(repo, number, since, state.get("sha"))
            if required is None:
                required = required_checks(repo, snap["base"])
                log("required checks: %s" % (", ".join(sorted(required)) or "none, gating on every check"))
            threads = unresolved_threads(repo, number) if a.until == "ready" else 0
            failures = 0
        except GhError as e:
            failures += 1
            log("GitHub error (%d in a row): %s" % (failures, e))
            if failures >= 10:
                emit("[unreachable] %s" % e)
                return 1
            time.sleep(interval * min(failures, 4))
            continue
        except (KeyError, TypeError) as e:
            log("unexpected response from GitHub: %r" % e)
            return 2

        events, code = evaluate(snap, state, required, a.until, me, time.time(), a.bot_grace, threads)
        # A two-minute overlap: `since` filters on update time, and seen ids drop the repeats.
        state["since"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(poll_started - 120))
        save_state(path, state)
        for e in events:
            emit(e)
        if code is not None:
            return code
        if time.time() > deadline:
            emit("[timeout] still waiting after %d min; start pr_watch again" % a.max_wait)
            return 3
        time.sleep(interval)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Watch a GitHub PR and print one line per event.")
    ap.add_argument("pr", help="PR number or URL")
    ap.add_argument("--repo", help="owner/name (default: from the URL or the current checkout)")
    ap.add_argument("--until", choices=("green", "ready", "any"), default="ready")
    ap.add_argument("--interval", type=int, default=30, help="seconds between polls (at least 15)")
    ap.add_argument("--max-wait", type=int, default=55, help="minutes before giving up with exit 3")
    ap.add_argument("--bot-grace", type=int, default=15,
                    help="minutes to wait for review bots after the checks go green")
    a = ap.parse_args(argv)

    try:
        repo, number = parse_target(a.pr, a.repo)
        me = (gh(["api", "user"]) or {}).get("login", "")
    except (ValueError, GhError, KeyError, TypeError) as e:
        log(str(e))
        return 2

    os.makedirs(STATE_DIR, exist_ok=True)
    lock = open(state_path(repo, number) + ".lock", "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("another pr_watch already watches %s#%d; don't start a second one" % (repo, number))
        return 2
    try:
        return watch(repo, number, a, me)
    except KeyboardInterrupt:
        return 3
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
