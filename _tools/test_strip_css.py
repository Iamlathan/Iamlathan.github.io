"""Tests for strip_css.py. Every test uses made up CSS or a temp folder; the real site is never written.
Only the Real file test reads assets/gcd.css (read only) and strips it in memory.
Run from the site folder:  python3 -m unittest discover -s _tools -p "test_*.py"
"""
import contextlib
import hashlib
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import strip_css as sc  # noqa: E402

REAL_CSS = os.path.join(os.path.dirname(TOOLS), "assets", "gcd.css")


def strip(text):
    return sc.strip_comments(text)[0]


class Comments(unittest.TestCase):
    def test_comment_between_rules_goes(self):
        self.assertEqual(strip("a{color:red}/* x */b{top:0}"), "a{color:red}b{top:0}")

    def test_comment_inside_a_rule_goes_and_the_spaces_around_it_stay(self):
        self.assertEqual(strip("a{color:red; /* x */ top:0}"), "a{color:red;  top:0}")

    def test_comment_alone_on_a_line_takes_its_line(self):
        self.assertEqual(strip("a{}\n/* x */\nb{}\n"), "a{}\nb{}\n")

    def test_indented_comment_line_goes_with_its_indent(self):
        self.assertEqual(strip("@media (x){\n  /* x */\n  a{}\n}\n"), "@media (x){\n  a{}\n}\n")

    def test_comment_over_many_lines_goes(self):
        self.assertEqual(strip("/*\n  head\n  more\n*/\na{}\n"), "a{}\n")

    def test_comment_at_line_end_takes_the_space_before_it(self):
        self.assertEqual(strip("a{} /* x */\nb{}\n"), "a{}\nb{}\n")

    def test_comment_at_file_end(self):
        self.assertEqual(strip("a{}\n/* x */"), "a{}\n")
        self.assertEqual(strip("a{} /* x */"), "a{}")

    def test_two_comments_in_a_row(self):
        self.assertEqual(strip("a{}/* x *//* y */\nb{}\n"), "a{}\nb{}\n")
        self.assertEqual(strip("a{}\n/* x */ /* y */\nb{}\n"), "a{}\nb{}\n")

    def test_blank_lines_that_were_there_stay(self):
        self.assertEqual(strip("a{}\n\nb{}\n"), "a{}\n\nb{}\n")
        self.assertEqual(strip("a{}\n\n/* x */\nb{}\n"), "a{}\n\nb{}\n")

    def test_crlf_lines(self):
        self.assertEqual(strip("a{}\r\n/* x */\r\nb{}\r\n"), "a{}\r\nb{}\r\n")
        self.assertEqual(strip("a{} /* x */\r\nb{}\r\n"), "a{}\r\nb{}\r\n")

    def test_counts(self):
        out, removed, kept = sc.strip_comments("/* a */\nx/* b */y{}\n/* c *//* d */\n")
        self.assertEqual(out, "x/**/y{}\n")
        self.assertEqual((removed, kept), (4, 1))


class Glued(unittest.TestCase):
    """Where taking a comment out would join two pieces of code into one, an empty /**/ stays."""

    def test_two_names(self):
        self.assertEqual(strip("div/* x */p{}"), "div/**/p{}")

    def test_number_and_unit(self):
        self.assertEqual(strip("a{top:1/* x */px}"), "a{top:1/**/px}")

    def test_slash_and_star(self):
        self.assertEqual(strip("a{b:1//* x */*2}"), "a{b:1//**/*2}")

    def test_dashes_and_angle(self):
        self.assertEqual(strip("--/* x */>"), "--/**/>")

    def test_name_and_bracket(self):
        self.assertEqual(strip("a{b:c/* x */(1)}"), "a{b:c/**/(1)}")

    def test_escaped_brace_is_not_a_safe_neighbor(self):
        self.assertEqual(strip(".x\\{/* x */a{}"), ".x\\{/**/a{}")

    def test_safe_neighbors_need_nothing(self):
        for src, want in [("a{}/* x */b{}", "a{}b{}"), ("a/* x */{}", "a{}"), ("a/* x */:hover{}", "a:hover{}"),
                          ("a{b:1;/* x */c:2}", "a{b:1;c:2}"), ("a,/* x */b{}", "a,b{}"), ("/* x */a{}", "a{}")]:
            with self.subTest(src=src):
                self.assertEqual(strip(src), want)


class KeptAsIs(unittest.TestCase):
    def assertSame(self, text):
        self.assertEqual(strip(text), text)

    def test_no_comments_no_change(self):
        self.assertSame("a{color:red}\n\n@media (max-width:600px){a{top:0}}\n")

    def test_strings(self):
        self.assertSame('a::before{content:"/* not a comment */"}')
        self.assertSame("a::before{content:'/* not */'}")
        self.assertSame('a::before{content:"say \\"/* hi */\\""}')
        self.assertSame("a::before{content:'it\\'s /* x */'}")

    def test_string_with_an_escaped_line_break(self):
        self.assertSame('a::before{content:"one\\\ntwo /* x */"}')

    def test_quoted_url(self):
        self.assertSame('a{background:url("/img/a/*b*/.png")}')
        self.assertSame("a{background:URL( '/img/*x*/.png' )}")

    def test_unquoted_url(self):
        self.assertSame("a{background:url(/img/a/*b*/.png)}")
        self.assertSame("a{background:url( data:image/svg+xml;utf8,<svg>/*</svg> )}")
        self.assertSame("a{background:url(/a\\)/*b.png)}")

    def test_a_function_ending_in_url_is_not_url(self):
        self.assertEqual(strip("a{b:myurl(/* x */c)}"), "a{b:myurl(c)}")
        self.assertEqual(strip("a{b:-url(/* x */c)}"), "a{b:-url(c)}")

    def test_escaped_slash_is_not_a_comment(self):
        self.assertSame(".a\\/*b{}")

    def test_single_slash(self):
        self.assertSame("a{grid-area:1/2/3/4;aspect-ratio:16/9}")

    def test_running_twice_changes_nothing(self):
        once = strip("/* a */\nx/* b */y{}\na{content:'/*'} /* c */\n")
        self.assertEqual(strip(once), once)


class Refuses(unittest.TestCase):
    def test_unclosed_comment(self):
        with self.assertRaisesRegex(ValueError, "comment.*line 2"):
            sc.strip_comments("a{}\n/* open\nb{}")

    def test_unclosed_string(self):
        with self.assertRaisesRegex(ValueError, "string.*line 1"):
            sc.strip_comments('a::before{content:"open\n}')

    def test_unclosed_url(self):
        with self.assertRaisesRegex(ValueError, "url.*line 1"):
            sc.strip_comments("a{background:url(/x.png}")


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gcd-strip-test-")
        self.src_dir = os.path.join(self.tmp, "assets")
        os.mkdir(self.src_dir)
        self.src = os.path.join(self.src_dir, "site.css")
        self.text = "/* head */\na{color:red} /* tail */\nb{top:0}\n"
        with open(self.src, "w", encoding="utf-8", newline="") as f:
            f.write(self.text)
        self.src_hash = self.hash(self.src)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def hash(self, path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sc.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def files(self):
        return sorted(os.path.relpath(os.path.join(d, n), self.tmp) for d, _, ns in os.walk(self.tmp) for n in ns)

    def test_default_prints_sizes_and_writes_nothing(self):
        before = self.files()
        code, out, _ = self.run_cli(self.src)
        self.assertEqual(code, 0)
        self.assertEqual(self.files(), before)
        self.assertIn("raw %d -> %d bytes" % (len(self.text), len("a{color:red}\nb{top:0}\n")), out)
        self.assertRegex(out, r"gzip -9 \d+ -> \d+ bytes")
        self.assertIn("2 comments removed", out)
        self.assertEqual(self.hash(self.src), self.src_hash)

    def test_out_writes_the_copy_and_leaves_the_source(self):
        dest = os.path.join(self.tmp, "publish")
        code, out, _ = self.run_cli(self.src, "--out", dest)
        self.assertEqual(code, 0)
        with open(os.path.join(dest, "site.css"), encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), "a{color:red}\nb{top:0}\n")
        self.assertEqual(self.hash(self.src), self.src_hash)
        self.assertIn("wrote", out)

    def test_more_than_one_file(self):
        other = os.path.join(self.src_dir, "more.css")
        with open(other, "w", encoding="utf-8") as f:
            f.write("c{}/* x */\n")
        dest = os.path.join(self.tmp, "publish")
        code, _, _ = self.run_cli(self.src, other, "--out", dest)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(dest)), ["more.css", "site.css"])

    def test_refuses_the_source_folder(self):
        same = [self.src_dir, self.src_dir + "/", os.path.join(self.src_dir, "."),
                os.path.join(self.tmp, "x", "..", "assets")]
        os.mkdir(os.path.join(self.tmp, "x"))
        upper = os.path.join(self.tmp, "ASSETS")
        if os.path.isdir(upper):
            same.append(upper)  # the Mac disk ignores letter case
        link = os.path.join(self.tmp, "link")
        os.symlink(self.src_dir, link)
        same.append(link)
        for dest in same:
            with self.subTest(dest=dest):
                code, _, err = self.run_cli(self.src, "--out", dest)
                self.assertNotEqual(code, 0)
                self.assertIn("source", err)
                self.assertEqual(self.hash(self.src), self.src_hash)
                self.assertEqual(os.listdir(self.src_dir), ["site.css"])

    def assertRefusedAndUntouched(self, code, err):
        self.assertNotEqual(code, 0)
        self.assertIn("source", err)
        self.assertEqual(self.hash(self.src), self.src_hash)
        self.assertEqual(os.listdir(self.src_dir), ["site.css"])

    def test_refuses_the_source_folder_through_a_missing_folder(self):
        # nope/ does not exist: the run must not make it, and nope/../assets is still the source folder
        for dest in (os.path.join(self.tmp, "nope", "..", "assets"),
                     os.path.join(self.tmp, "nope", "deeper", "..", "..", "assets")):
            with self.subTest(dest=dest):
                code, _, err = self.run_cli(self.src, "--out", dest)
                self.assertRefusedAndUntouched(code, err)
                self.assertFalse(os.path.exists(os.path.join(self.tmp, "nope")))

    def test_refuses_a_link_to_a_source_in_the_out_folder(self):
        dest = os.path.join(self.tmp, "publish")
        os.mkdir(dest)
        os.symlink(self.src, os.path.join(dest, "site.css"))
        code, _, err = self.run_cli(self.src, "--out", dest)
        self.assertRefusedAndUntouched(code, err)
        self.assertTrue(os.path.islink(os.path.join(dest, "site.css")))

    def test_refuses_a_hard_link_to_a_source_in_the_out_folder(self):
        dest = os.path.join(self.tmp, "publish")
        os.mkdir(dest)
        os.link(self.src, os.path.join(dest, "site.css"))
        code, _, err = self.run_cli(self.src, "--out", dest)
        self.assertRefusedAndUntouched(code, err)

    def test_refuses_a_link_to_another_source(self):
        other_dir = os.path.join(self.tmp, "more")
        os.mkdir(other_dir)
        other = os.path.join(other_dir, "more.css")
        with open(other, "w", encoding="utf-8") as f:
            f.write("c{}/* x */\n")
        dest = os.path.join(self.tmp, "publish")
        os.mkdir(dest)
        os.symlink(self.src, os.path.join(dest, "more.css"))
        code, _, err = self.run_cli(self.src, other, "--out", dest)
        self.assertRefusedAndUntouched(code, err)
        self.assertEqual(os.listdir(dest), ["more.css"])

    def test_refuses_any_link_at_the_destination(self):
        # a link that points somewhere else (here at a file not made yet) would be followed by a plain write
        dest = os.path.join(self.tmp, "publish")
        os.mkdir(dest)
        os.symlink(os.path.join(self.tmp, "elsewhere.css"), os.path.join(dest, "site.css"))
        code, _, err = self.run_cli(self.src, "--out", dest)
        self.assertNotEqual(code, 0)
        self.assertIn("link", err)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "elsewhere.css")))

    def test_an_old_copy_in_the_out_folder_is_replaced(self):
        dest = os.path.join(self.tmp, "publish")
        os.mkdir(dest)
        with open(os.path.join(dest, "site.css"), "w", encoding="utf-8") as f:
            f.write("old copy\n")
        code, _, _ = self.run_cli(self.src, "--out", dest)
        self.assertEqual(code, 0)
        with open(os.path.join(dest, "site.css"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "a{color:red}\nb{top:0}\n")
        self.assertEqual(self.hash(self.src), self.src_hash)

    def test_refuses_two_files_with_one_name(self):
        os.mkdir(os.path.join(self.tmp, "b"))
        twin = os.path.join(self.tmp, "b", "site.css")
        shutil.copy(self.src, twin)
        dest = os.path.join(self.tmp, "publish")
        code, _, err = self.run_cli(self.src, twin, "--out", dest)
        self.assertNotEqual(code, 0)
        self.assertIn("same name", err)
        self.assertFalse(os.path.exists(dest))

    def test_a_bad_file_stops_the_run_before_any_write(self):
        bad = os.path.join(self.src_dir, "bad.css")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("a{}/* open\n")
        dest = os.path.join(self.tmp, "publish")
        code, _, err = self.run_cli(self.src, bad, "--out", dest)
        self.assertNotEqual(code, 0)
        self.assertIn("bad.css", err)
        self.assertFalse(os.path.exists(dest))


@unittest.skipUnless(os.path.exists(REAL_CSS), "assets/gcd.css not found")
class RealFile(unittest.TestCase):
    """Reads the real style file (never writes it) and checks the stripped text in memory."""

    @classmethod
    def setUpClass(cls):
        with open(REAL_CSS, encoding="utf-8", newline="") as f:
            cls.src = f.read()
        cls.out, cls.removed, cls.kept = sc.strip_comments(cls.src)

    def test_it_has_comments_and_they_all_go(self):
        self.assertGreater(self.removed, 0)
        self.assertEqual(sc.strip_comments(self.out)[1:], (self.kept, self.kept))
        self.assertEqual(strip(self.out), self.out)

    def test_smaller(self):
        self.assertLess(len(self.out), len(self.src))

    def test_every_url_and_string_is_kept(self):
        pattern = r"url\([^)]*\)|\"[^\"\n]*\"|'[^'\n]*'"
        self.assertEqual(re.findall(pattern, self.out), re.findall(pattern, re.sub(r"/\*.*?\*/", "", self.src, flags=re.S)))


if __name__ == "__main__":
    unittest.main()
