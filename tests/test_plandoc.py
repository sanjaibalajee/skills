"""Tests for skills/plan-doc/scripts/plandoc.py. Run: python3 -m unittest discover tests"""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "plandoc", os.path.join(ROOT, "skills", "plan-doc", "scripts", "plandoc.py"))
plandoc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plandoc)
EXAMPLE = os.path.join(ROOT, "examples", "plan-doc", "webhook-retries.html")


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = plandoc.main(list(argv))
    return code, out.getvalue()


class TestPlandoc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def test_new_fills_meta_and_refuses_overwrite(self):
        code, out = run("new", "Hosting tab scope", "--out", self.tmp.name, "--author", "Test Author")
        self.assertEqual(code, 0)
        doc = plandoc.read_text(self.path("hosting-tab-scope.html"))
        self.assertIn("<title>Hosting tab scope</title>", doc)
        self.assertIn("Test Author", doc)
        self.assertNotIn("{{", doc)
        with self.assertRaises(SystemExit):
            run("new", "Hosting tab scope", "--out", self.tmp.name)

    def test_fresh_scaffold_fails_check(self):
        run("new", "Refund flow", "--out", self.tmp.name)
        code, out = run("check", self.path("refund-flow.html"), "--no-unslop")
        self.assertEqual(code, 1)
        self.assertIn("unfilled placeholder", out)

    def test_example_passes_check(self):
        code, out = run("check", EXAMPLE)
        self.assertEqual(code, 0, out)
        self.assertIn("0 errors, 0 warnings", out)

    def test_check_flags_title_literals_and_dashes(self):
        doc = plandoc.read_text(EXAMPLE)
        doc = doc.replace("<title>Webhook retries</title>", "<title>Plan</title>")
        doc = doc.replace("footer {", "footer { box-shadow: 0 1px 2px #000; color: #333;")
        doc = doc.replace("First draft.", "First draft — rough.")
        p = self.path("bad.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(doc)
        code, out = run("check", p, "--no-unslop")
        self.assertEqual(code, 1)
        self.assertIn("is a category, not a name", out)
        self.assertIn("color literal", out)
        self.assertIn("box-shadow", out)
        self.assertIn("em dash", out)

    def test_fragment_drops_wrapper(self):
        dest = self.path("frag.html")
        run("fragment", EXAMPLE, "-o", dest)
        frag = plandoc.read_text(dest)
        self.assertTrue(frag.startswith("<title>Webhook retries</title>"))
        for tag in ("<!doctype", "<html", "<head>", "<body", 'name="viewport"'):
            self.assertNotIn(tag, frag.lower())
        self.assertIn('<meta name="claude:viewport-fit-sides" content="cover">', frag)


if __name__ == "__main__":
    unittest.main()
