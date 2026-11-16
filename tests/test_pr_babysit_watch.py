import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("pr_watch", os.path.join(ROOT, "skills", "pr-babysit", "scripts", "pr_watch.py"))
pr_watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr_watch)

ME = "me"


def snap(sha="aaaaaaa1", checks=None, comments=None, merge="clean", state="open", merged=False, head_author=None):
    return {"state": state, "merged": merged, "sha": sha, "base": "main", "mergeable_state": merge,
            "checks": checks if checks is not None else {}, "comments": comments or [], "head_author": head_author}


def check(state, url="https://ci/1"):
    return {"state": state, "url": url}


def comment(cid, who, kind="comment", body="looks off", commit=None):
    return {"id": cid, "who": who, "kind": kind, "body": body, "url": "https://gh/c/" + cid, "commit": commit}


def run(s, state, until="ready", required=frozenset(), now=1000.0, threads=0, grace=15):
    return pr_watch.evaluate(s, state, set(required), until, ME, now, grace, threads)


class Evaluate(unittest.TestCase):
    def test_first_run_does_not_report_existing_comments(self):
        state = {}
        events, code = run(snap(comments=[comment("c1", "bob")], checks={"ci": check("pending")}), state)
        self.assertEqual(events, [])
        self.assertIsNone(code)
        events, _ = run(snap(comments=[comment("c1", "bob"), comment("c2", "bob")],
                             checks={"ci": check("pending")}), state)
        self.assertEqual(len(events), 1)
        self.assertIn("[comment] bob comment: looks off", events[0])

    def test_own_and_deploy_bot_comments_are_quiet(self):
        state = {}
        run(snap(checks={"ci": check("pending")}), state)
        events, _ = run(snap(checks={"ci": check("pending")}, comments=[
            comment("c1", ME), comment("c2", "vercel[bot]"), comment("c3", "coderabbitai[bot]")]), state)
        self.assertEqual(len(events), 1)
        self.assertIn("coderabbitai[bot]", events[0])

    def test_empty_commented_review_is_skipped_but_approval_is_not(self):
        state = {}
        run(snap(checks={"ci": check("pending")}), state)
        events, _ = run(snap(checks={"ci": check("pending")}, comments=[
            comment("r1", "bob", kind="review commented", body=""),
            comment("r2", "bob", kind="review approved", body="")]), state)
        self.assertEqual(len(events), 1)
        self.assertIn("review approved", events[0])

    def test_failed_required_check_exits_1_and_reports_once(self):
        state = {}
        s = snap(checks={"lint": check("failure"), "flaky": check("failure"), "test": check("success")})
        events, code = run(s, state, required={"lint", "test"})
        self.assertEqual(code, 1)
        self.assertEqual([e.split()[1] for e in events if e.startswith("[check-failed]")], ["lint"])
        events, _ = run(s, state, required={"lint", "test"})
        self.assertFalse(any(e.startswith("[check-failed]") for e in events))

    def test_green_with_required_ignores_optional_pending(self):
        state = {}
        s = snap(checks={"test": check("success"), "slow-optional": check("pending")})
        events, code = run(s, state, until="green", required={"test"})
        self.assertEqual(code, 0)
        self.assertEqual(events[-1], "[green]")

    def test_without_required_every_check_gates(self):
        state = {}
        _, code = run(snap(checks={"a": check("success"), "b": check("pending")}), state, until="green")
        self.assertIsNone(code)
        events, code = run(snap(checks={"a": check("success"), "b": check("skipped")}), state, until="green")
        self.assertEqual(code, 0)
        self.assertTrue(any(e.startswith("[checks-done]") for e in events))

    def test_repo_without_ci_goes_green_after_grace(self):
        state = {}
        _, code = run(snap(), state, until="green", now=1000.0)
        self.assertIsNone(code)
        _, code = run(snap(), state, until="green", now=1000.0 + pr_watch.NO_CHECKS_GRACE)
        self.assertEqual(code, 0)

    def test_ready_waits_for_bot_that_reviewed_an_older_commit(self):
        state = {}
        old_review = comment("r1", "greptile-apps[bot]", kind="review commented", body="ok", commit="old")
        s = snap(checks={"ci": check("success")}, comments=[old_review])
        _, code = run(s, state, now=1000.0)
        self.assertIsNone(code)
        new_review = comment("r2", "greptile-apps[bot]", kind="review commented", body="lgtm", commit="aaaaaaa1")
        events, code = run(snap(checks={"ci": check("success")}, comments=[old_review, new_review]), state, now=1060.0)
        self.assertEqual(code, 0)
        self.assertEqual(events[-1], "[ready]")

    def test_ready_stops_waiting_for_bots_after_grace(self):
        state = {}
        old_review = comment("r1", "greptile-apps[bot]", kind="review commented", body="ok", commit="old")
        s = snap(checks={"ci": check("success")}, comments=[old_review])
        run(s, state, now=1000.0)
        _, code = run(s, state, now=1000.0 + 15 * 60)
        self.assertEqual(code, 0)

    def test_ready_blocked_by_threads_and_behind(self):
        _, code = run(snap(checks={"ci": check("success")}), {}, threads=2)
        self.assertEqual(code, 1)
        events, code = run(snap(checks={"ci": check("success")}, merge="behind"), {})
        self.assertEqual(code, 1)
        self.assertIn("[behind] the base branch moved ahead", events)

    def test_conflict_exits_1(self):
        events, code = run(snap(checks={"ci": check("pending")}, merge="dirty"), {})
        self.assertEqual(code, 1)
        self.assertIn("[conflict]", events)

    def test_push_by_someone_else_is_reported_and_resets_green(self):
        state = {}
        run(snap(sha="aaaaaaa1", checks={"ci": check("success")}), state, until="any")
        self.assertTrue(state["green_at"])
        events, _ = run(snap(sha="bbbbbbb2", checks={"ci": check("pending")}, head_author="alice"), state, until="any")
        self.assertIn("[pushed] bbbbbbb by alice", events)
        self.assertIsNone(state["green_at"])
        events, _ = run(snap(sha="ccccccc3", checks={"ci": check("pending")}, head_author=ME), state, until="any")
        self.assertFalse(any(e.startswith("[pushed]") for e in events))

    def test_merged_and_closed(self):
        self.assertEqual(run(snap(merged=True, state="closed"), {}), (["[merged]"], 0))
        self.assertEqual(run(snap(state="closed"), {}), (["[closed]"], 1))

    def test_parse_target_from_url(self):
        self.assertEqual(pr_watch.parse_target("https://github.com/o/r/pull/42", None), ("o/r", 42))
        with self.assertRaises(ValueError):
            pr_watch.parse_target("abc", "o/r")


if __name__ == "__main__":
    unittest.main()
