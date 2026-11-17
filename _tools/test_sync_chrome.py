"""Tests for sync_chrome.py. Every test stamps a small made up site in a temp folder; the real pages are never
written. Only the Real copy test reads three real pages, copies them into a temp folder and stamps the copies.
Run from the site folder:  python3 -m unittest discover -s _tools -p "test_*.py"
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import sync_chrome as sc  # noqa: E402

REAL_ROOT = sc.ROOT

# The source page (home) carries the blocks with no current page marks.
SRC_HEADER = ('<header class="site-header" id="top">\n'
              '  <a class="brand" href="/">G</a>\n'
              '  <a href="/work/">Work</a>\n'
              '  <button class="nav-dd-btn">Services</button>\n'
              '  <a class="dd-item" href="/services/local-seo/">Local SEO</a>\n'
              '  <a class="dd-item" href="/services/care-plan/">Care Plan</a>\n'
              '  <a class="btn btn-primary btn-sm" href="/get-started/">Contact us</a>\n'
              '  <button class="menu-link menu-sub-btn">Services</button>\n'
              '  <a class="menu-sub-item" href="/services/local-seo/">Local SEO</a>\n'
              '</header>')
SRC_FOOTER = ('<footer class="site-footer">\n'
              '  <a class="brand" href="/">G</a>\n'
              '  <nav class="footer-col" aria-label="Services"><a href="/services/local-seo/">Local SEO</a>'
              '<a href="/services/care-plan/">Care Plan</a><a href="/get-started/">Free preview</a></nav>\n'
              '  <p class="footer-line">A made up footer line.</p>\n'
              '</footer>')
SRC_FBAR = ('<div class="fbar" role="region">\n'
            '  <a class="btn btn-primary btn-sm" href="/get-started/">Get my free preview</a>\n'
            '</div>')

# The same blocks as they should read on /services/local-seo/, written out by hand.
SEO_HEADER = ('<header class="site-header" id="top">\n'
              '  <a class="brand" href="/">G</a>\n'
              '  <a href="/work/">Work</a>\n'
              '  <button class="nav-dd-btn is-current">Services</button>\n'
              '  <a class="dd-item" href="/services/local-seo/" aria-current="page">Local SEO</a>\n'
              '  <a class="dd-item" href="/services/care-plan/">Care Plan</a>\n'
              '  <a class="btn btn-primary btn-sm" href="/get-started/">Contact us</a>\n'
              '  <button class="menu-link menu-sub-btn is-current">Services</button>\n'
              '  <a class="menu-sub-item" href="/services/local-seo/" aria-current="page">Local SEO</a>\n'
              '</header>')
SEO_FOOTER = ('<footer class="site-footer">\n'
              '  <a class="brand" href="/">G</a>\n'
              '  <nav class="footer-col" aria-label="Services"><a href="/services/local-seo/" aria-current="page">'
              'Local SEO</a><a href="/services/care-plan/">Care Plan</a><a href="/get-started/">Free preview</a></nav>\n'
              '  <p class="footer-line">A made up footer line.</p>\n'
              '</footer>')

# The slim header of /get-started/ (logo and Call only), its footer and its floating bar, written out by hand.
SLIM_HEADER = ('<header class="site-header" id="top">\n'
               '  <div class="bar bar-slim"><a class="brand" href="/">G</a><a href="tel:+15550000000">Call</a></div>\n'
               '</header>')
START_FOOTER = ('<footer class="site-footer">\n'
                '  <a class="brand" href="/">G</a>\n'
                '  <nav class="footer-col" aria-label="Services"><a href="/services/local-seo/">Local SEO</a>'
                '<a href="/services/care-plan/">Care Plan</a><a href="/get-started/" aria-current="page">Free preview</a>'
                '</nav>\n'
                '  <p class="footer-line">A made up footer line.</p>\n'
                '</footer>')
START_FBAR = ('<div class="fbar" role="region">\n'
              '  <a class="btn btn-primary btn-sm" href="#start">Get my free preview</a>\n'
              '</div>')

# A footer someone edited by hand on one page: a link renamed, one dropped, a line added.
HAND_FOOTER = ('<footer class="site-footer">\n'
               '  <a class="brand" href="/">G</a>\n'
               '  <nav class="footer-col" aria-label="Services"><a href="/services/local-seo/">Local search</a></nav>\n'
               '  <p class="footer-line">A made up footer line.</p>\n'
               '  <p>A line added by hand.</p>\n'
               '</footer>')

MAIN_23 = ["index.html", "about/index.html", "client-portal/index.html", "contact/index.html", "faq/index.html",
           "free-check/index.html", "get-started/index.html", "privacy/index.html", "terms/index.html",
           "service-area/index.html", "work/index.html", "services/care-plan/index.html",
           "services/free-website-check/index.html", "services/website-design/index.html",
           "services/website-rebuild/index.html", "404.html",
           "services/google-business-profile/index.html", "services/local-seo/index.html",
           "services/logo-and-brand-kit/index.html", "websites-for/home-services/index.html",
           "websites-for/auto-shops/index.html", "websites-for/food-and-coffee/index.html",
           "websites-for/beauty-and-wellness/index.html"]


def page(header, footer, fbar, body="<main><h1>Made up page</h1></main>"):
    return "<!doctype html>\n<html><body>\n%s\n%s\n%s\n%s\n</body></html>\n" % (header, body, footer, fbar)


def put(root, relpath, text):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class StampBase(unittest.TestCase):
    """A small made up site in a temp folder with the source page on it. Holds no tests."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gcd-chrome-test-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(setattr, sc, "ROOT", sc.ROOT)
        sc.ROOT = self.root
        put(self.root, "index.html", page(SRC_HEADER, SRC_FOOTER, SRC_FBAR))

    def run_tool(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sc.main(list(argv))
        return code, out.getvalue()

    def text(self, relpath):
        return read(os.path.join(self.root, relpath))


class Stamp(StampBase):

    def test_stamped_page_is_left_byte_for_byte(self):
        stamped = page(SEO_HEADER, SEO_FOOTER, SRC_FBAR)
        put(self.root, "services/local-seo/index.html", stamped)
        code, out = self.run_tool("services/local-seo/index.html")
        self.assertEqual(code, 0)
        self.assertEqual(self.text("services/local-seo/index.html"), stamped)
        self.assertIn("unchanged", out)
        self.assertNotIn("updated", out)

    def test_second_run_changes_nothing(self):
        put(self.root, "services/local-seo/index.html", page(SEO_HEADER, HAND_FOOTER, SRC_FBAR))
        self.run_tool("services/local-seo/index.html")
        first = self.text("services/local-seo/index.html")
        code, out = self.run_tool("services/local-seo/index.html")
        self.assertEqual(code, 0)
        self.assertEqual(self.text("services/local-seo/index.html"), first)
        self.assertIn("unchanged", out)

    def test_hand_edited_footer_gets_the_source_footer_back(self):
        body = "<main><h1>Local SEO</h1><p>Body text stays.</p></main>"
        put(self.root, "services/local-seo/index.html", page(SEO_HEADER, HAND_FOOTER, SRC_FBAR, body))
        code, out = self.run_tool("services/local-seo/index.html")
        self.assertEqual(code, 0)
        self.assertEqual(self.text("services/local-seo/index.html"), page(SEO_HEADER, SEO_FOOTER, SRC_FBAR, body))
        self.assertIn("footer updated", out)

    def test_stale_header_gets_this_pages_marks(self):
        put(self.root, "services/local-seo/index.html", page(SRC_HEADER, SEO_FOOTER, SRC_FBAR))
        self.run_tool("services/local-seo/index.html")
        self.assertEqual(self.text("services/local-seo/index.html"), page(SEO_HEADER, SEO_FOOTER, SRC_FBAR))

    def test_slim_get_started_header_is_left_alone(self):
        put(self.root, "get-started/index.html", page(SLIM_HEADER, HAND_FOOTER, SRC_FBAR))
        code, out = self.run_tool("get-started/index.html")
        self.assertEqual(code, 0)
        self.assertEqual(self.text("get-started/index.html"), page(SLIM_HEADER, START_FOOTER, START_FBAR))
        self.assertIn("slim header kept", out)

    def test_path_outside_the_site_is_refused(self):
        outside = tempfile.mkdtemp(prefix="gcd-chrome-outside-")
        self.addCleanup(shutil.rmtree, outside, True)
        stale = page(SRC_HEADER, HAND_FOOTER, SRC_FBAR)
        put(outside, "index.html", stale)
        rel = os.path.relpath(os.path.join(outside, "index.html"), self.root)
        for arg in (os.path.join(outside, "index.html"), rel):
            code, out = self.run_tool(arg)
            self.assertIn("outside", out)
            self.assertNotIn("changed", out)
        self.assertEqual(read(os.path.join(outside, "index.html")), stale)

    def test_link_inside_the_site_that_points_outside_is_refused(self):
        outside = tempfile.mkdtemp(prefix="gcd-chrome-outside-")
        self.addCleanup(shutil.rmtree, outside, True)
        stale = page(SRC_HEADER, HAND_FOOTER, SRC_FBAR)
        put(outside, "index.html", stale)
        os.symlink(outside, os.path.join(self.root, "linked"))
        code, out = self.run_tool("linked/index.html")
        self.assertIn("outside", out)
        self.assertEqual(read(os.path.join(outside, "index.html")), stale)

    def test_sample_designs_are_refused(self):
        stale = page(SRC_HEADER, HAND_FOOTER, SRC_FBAR)
        for rel in ("samples/acme/index.html", "designs/bluebird/index.html", "sample/index.html"):
            put(self.root, rel, stale)
            code, out = self.run_tool(rel)
            self.assertIn("refused", out)
            self.assertEqual(self.text(rel), stale)

    def test_sample_designs_are_refused_in_any_letter_case(self):
        # The Mac disk ignores letter case, so Samples/ opens the same folder as samples/.
        # Each folder is made with the odd case itself, so the test holds on a case sensitive disk too.
        stale = page(SRC_HEADER, HAND_FOOTER, SRC_FBAR)
        for rel in ("Samples/acme/index.html", "DESIGNS/bluebird/index.html", "Sample/index.html",
                    "sAmPlEs/index.html"):
            put(self.root, rel, stale)
            code, out = self.run_tool(rel)
            self.assertIn("refused", out, rel)
            self.assertNotIn("changed", out, rel)
            self.assertEqual(self.text(rel), stale, rel)

    def test_check_mode_reports_and_writes_nothing(self):
        stale = page(SEO_HEADER, HAND_FOOTER, SRC_FBAR)
        put(self.root, "services/local-seo/index.html", stale)
        code, out = self.run_tool("--check", "services/local-seo/index.html")
        self.assertEqual(code, 1)
        self.assertIn("would change", out)
        self.assertIn("footer updated", out)
        self.assertEqual(self.text("services/local-seo/index.html"), stale)

    def test_check_mode_exits_0_when_all_in_step(self):
        put(self.root, "services/local-seo/index.html", page(SEO_HEADER, SEO_FOOTER, SRC_FBAR))
        code, out = self.run_tool("--check", "services/local-seo/index.html")
        self.assertEqual(code, 0)


class PageList(unittest.TestCase):

    def test_default_list_is_the_23_main_pages_plus_the_work_template(self):
        self.assertEqual(sorted(sc.MAIN_PAGES), sorted(MAIN_23 + ["_tools/templates/work.html"]))

    def test_root_is_the_folder_above_tools(self):
        self.assertEqual(os.path.realpath(REAL_ROOT), os.path.realpath(os.path.dirname(TOOLS)))

    def test_tools_name_no_local_folder(self):
        for name in ("sync_chrome.py", "blocks_check.py"):
            text = read(os.path.join(TOOLS, name))
            for bit in ("/Users/", "/home/", "C:\\"):
                self.assertNotIn(bit, text, name)


class RealCopy(StampBase):
    """Copies three real pages into the temp folder (reading only) and stamps the copies twice."""

    PAGES = ("index.html", "services/local-seo/index.html", "get-started/index.html")

    def test_real_page_copies_settle_after_one_run(self):
        for rel in self.PAGES:
            src = os.path.join(REAL_ROOT, rel)
            if not os.path.isfile(src):
                self.skipTest("real page missing: " + rel)
            put(self.root, rel, read(src))
        self.run_tool(*self.PAGES)
        first = {rel: self.text(rel) for rel in self.PAGES}
        code, out = self.run_tool("--check", *self.PAGES)
        self.assertEqual(code, 0, out)
        self.assertEqual({rel: self.text(rel) for rel in self.PAGES}, first)
        self.assertIn("slim header kept", out)


if __name__ == "__main__":
    unittest.main()
