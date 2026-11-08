"""Tests for skills/unslop/scripts/scan.py. Run: python3 -m unittest discover tests"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "scan", os.path.join(ROOT, "skills", "unslop", "scripts", "scan.py"))
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


class ScanCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)  # keep a stray .unslop.json from leaking in

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def run_scan(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = scan.main(list(args) + ["--format", "json"])
        return code, json.loads(out.getvalue())

    def rules(self, report):
        return {f["rule"] for r in report for f in r["findings"]}


class TestProse(ScanCase):
    def test_flags_common_tells(self):
        p = self.write("a.md", "Certainly! We leverage a robust queue — it plays a crucial role.\n")
        _, rep = self.run_scan(p)
        self.assertTrue({"chatbot-opener", "buzzword", "em-dash", "ai-vocab"} <= self.rules(rep))

    def test_skips_code_urls_and_front_matter(self):
        p = self.write("b.md", "---\ntitle: robust\n---\n```\nseamless delve\n```\n"
                               "Call `leverage()` at https://x.dev/robust.\n")
        _, rep = self.run_scan(p)
        self.assertEqual(self.rules(rep), set())

    def test_region_and_line_suppression(self):
        p = self.write("c.md", "<!-- unslop:off -->\nDelve into the tapestry.\n<!-- unslop:on -->\n"
                               "Robust thing. <!-- unslop:ignore -->\n")
        _, rep = self.run_scan(p)
        self.assertEqual(self.rules(rep), set())

    def test_title_case_heading(self):
        p = self.write("d.md", "# Our Complete Rollout Strategy\n\n## Rollout plan for events\n")
        _, rep = self.run_scan(p)
        heads = [f for f in rep[0]["findings"] if f["rule"] == "title-case-heading"]
        self.assertEqual([f["line"] for f in heads], [1])

    def test_bold_label_bullet_only_with_colon(self):
        p = self.write("e.md", "- **Speed:** fast\n- **Schema in one file.** Tables live there.\n")
        _, rep = self.run_scan(p)
        hits = [f["line"] for f in rep[0]["findings"] if f["rule"] == "bold-label-bullet"]
        self.assertEqual(hits, [1])


class TestHtml(ScanCase):
    def test_visible_text_only(self):
        p = self.write("p.html", "<style>.a{content:'delve'}</style><script>let s='robust'</script>"
                                 "<pre>seamless</pre><p>Queue&mdash;done.</p>"
                                 "<ul><li><strong>Risk:</strong> low</li></ul>")
        _, rep = self.run_scan(p)
        self.assertEqual(self.rules(rep), {"em-dash", "bold-label-bullet"})


class TestCommit(ScanCase):
    def test_trailer_fails_strict(self):
        p = self.write("m.txt", "fix: refund retries\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
        code, rep = self.run_scan("--commit-msg", p, "--strict")
        self.assertEqual(code, 1)
        self.assertIn("ai-attribution", self.rules(rep))

    def test_clean_commit_passes(self):
        p = self.write("m.txt", "fix: refund retries\n# comment lines are ignored, robust\n")
        code, rep = self.run_scan("--commit-msg", p, "--strict")
        self.assertEqual((code, self.rules(rep)), (0, set()))

    def test_subject_checks(self):
        p = self.write("m.txt", "Added the retry logic to the refund worker so failed captures recover later.\n")
        _, rep = self.run_scan("--commit-msg", p)
        self.assertTrue({"commit-subject-length", "commit-subject-mood", "commit-subject-period"}
                        <= self.rules(rep))


class TestDiff(ScanCase):
    DIFF = """diff --git a/README.md b/README.md
index 1..2 100644
--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # title
-robust old line
+A seamless new line.
 context
diff --git a/app/w.py b/app/w.py
--- a/app/w.py
+++ b/app/w.py
@@ -10,0 +11,2 @@
+# Retries robustly, ensuring delivery.
+x = "seamless string"
"""

    def test_added_lines_and_code_comments_only(self):
        p = self.write("d.diff", self.DIFF)
        _, rep = self.run_scan("--diff", p)
        by_file = {r["file"]: r["findings"] for r in rep}
        self.assertEqual([f["line"] for f in by_file["README.md"]], [2])
        self.assertEqual({f["rule"] for f in by_file["app/w.py"]}, {"ing-tail"})
        self.assertTrue(all(f["line"] == 11 for f in by_file["app/w.py"]))


class TestDictationAndConfig(ScanCase):
    def test_dictation_is_opt_in(self):
        p = self.write("v.txt", "So uh the the refund email, sorry, the WhatsApp template goes out.\n")
        _, plain = self.run_scan(p)
        _, dict_ = self.run_scan(p, "--dictation")
        self.assertNotIn("self-correction", self.rules(plain))
        self.assertTrue({"dictation-filler", "repeated-word", "self-correction"} <= self.rules(dict_))

    def test_config_allow_disable_and_house_rule(self):
        self.write(".unslop.json", json.dumps({
            "allow": ["robust"], "disable": ["em-dash"],
            "rules": [{"id": "old-name", "pattern": r"\boutworld\b", "severity": "high"}]}))
        p = self.write("f.md", "A robust page — on Outworld.\n")
        _, rep = self.run_scan(p)
        self.assertEqual(self.rules(rep), {"old-name"})


if __name__ == "__main__":
    unittest.main()
