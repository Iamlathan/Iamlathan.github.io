"""Tests for make_small_shots.py. Every test works on made up pictures in a temp folder; the real site is never
written. The pictures are made with the real cwebp and dwebp, so the tests are skipped on a Mac without them.
Run from the site folder:  python3 -m unittest discover -s _tools -p "test_*.py"
"""
import contextlib
import io
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402
import make_small_shots as ms  # noqa: E402

REAL_ROOT = bp.ROOT
TOOLS = ms.find_tools()


def png_bytes(w, h, seed):
    """A real PNG of w x h: soft colour bands with a little grain, different for each seed."""
    rnd = random.Random(seed)
    base = [rnd.randrange(40, 200) for _ in range(3)]
    top = bytes((base[i % 3] + (i // 3) // 8 + rnd.randrange(0, 24)) % 256 for i in range(w * 3))
    rows = [b"\x00" + top.translate(bytes((v + y // 4) % 256 for v in range(256))) for y in range(h)]

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 1)) + chunk(b"IEND", b""))


@unittest.skipUnless(TOOLS, "cwebp and dwebp are not on this Mac")
class SmallShots(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gcd-test-")
        bp.set_root(self.root)
        self.folder = os.path.join(self.root, "work", "shots", "desktop")
        os.makedirs(self.folder)

    def tearDown(self):
        bp.set_root(REAL_ROOT)
        shutil.rmtree(self.root, ignore_errors=True)

    def big(self, slug, w, h, seed=1):
        """Write work/shots/desktop/<slug>.webp as a real WebP of w x h and return its bytes."""
        png = os.path.join(self.root, "src.png")
        with open(png, "wb") as f:
            f.write(png_bytes(w, h, seed))
        out = os.path.join(self.folder, slug + ".webp")
        subprocess.run([TOOLS[1], "-quiet", "-q", "60", png, "-o", out], check=True)
        return self.data(slug)

    def data(self, name):
        with open(os.path.join(self.folder, name + ".webp"), "rb") as f:
            return f.read()

    def size(self, name):
        return bp.image_size(os.path.join(self.folder, name + ".webp"))

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ms.main(list(args))
        return code, out.getvalue()

    def test_makes_an_800_wide_copy_and_leaves_the_big_file_alone(self):
        before = self.big("test-shop", 1200, 750)
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.size("test-shop-800"), (800, 500))
        self.assertEqual(self.data("test-shop"), before)
        self.assertEqual(sorted(os.listdir(self.folder)), ["test-shop-800.webp", "test-shop.webp"])
        self.assertIn("work/shots/desktop/test-shop-800.webp: 800 x 500, q82", out)

    def test_a_1920_wide_shot_also_comes_out_800_wide_in_the_same_shape(self):
        self.big("wide-shop", 1920, 1200)
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.size("wide-shop-800"), (800, 500))

    def test_the_copy_is_the_same_picture_as_the_big_file(self):
        # two different big pictures give two different copies, and the same big picture gives the same copy
        self.big("shop-a", 1000, 100, seed=1)
        self.big("shop-b", 1000, 100, seed=2)
        self.assertEqual(self.run_main()[0], 0)
        a1, b1 = self.data("shop-a-800"), self.data("shop-b-800")
        self.assertNotEqual(a1, b1)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.data("shop-a-800"), a1)
        # the big shot is retaken: the old copy is replaced by one made from the new picture
        self.big("shop-a", 1000, 100, seed=2)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.data("shop-a-800"), b1)

    def test_copies_are_never_used_as_a_source(self):
        self.big("test-shop", 1000, 100)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(sorted(os.listdir(self.folder)), ["test-shop-800.webp", "test-shop.webp"])

    def test_a_shot_that_is_not_wider_than_800_gets_no_copy(self):
        self.big("narrow-shop", 800, 100)
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertEqual(os.listdir(self.folder), ["narrow-shop.webp"])
        self.assertIn("narrow-shop.webp is 800 px wide, so it needs no copy", out)

    def test_a_file_in_the_way_that_is_not_an_800_copy_is_left_alone(self):
        # a design whose own name ends in -800 keeps its 1000 px shot: the copy for "route" is not written over it
        self.big("route", 1000, 100, seed=1)
        own = self.big("route-800", 1000, 100, seed=2)
        code, out = self.run_main()
        self.assertEqual(code, 1, out)
        self.assertEqual(self.data("route-800"), own)
        self.assertIn("work/shots/desktop/route-800.webp is not an 800 px copy (1000 px wide), left alone", out)
        self.assertEqual(sorted(os.listdir(self.folder)), ["route-800.webp", "route.webp"])

    def test_a_link_in_the_way_is_left_alone_and_what_it_points_at_is_not_changed(self):
        # the link points at a real 800 px copy, so only the link check can stop it
        self.big("route", 1000, 100, seed=1)
        self.assertEqual(self.run_main()[0], 0)
        elsewhere = os.path.join(self.root, "elsewhere.webp")
        shutil.move(os.path.join(self.folder, "route-800.webp"), elsewhere)
        self.assertEqual(bp.image_size(elsewhere), (800, 80))
        self.big("route", 1000, 100, seed=2)
        with open(elsewhere, "rb") as f:
            before = f.read()
        os.symlink(elsewhere, os.path.join(self.folder, "route-800.webp"))
        code, out = self.run_main()
        self.assertEqual(code, 1, out)
        self.assertIn("left alone", out)
        self.assertTrue(os.path.islink(os.path.join(self.folder, "route-800.webp")))
        with open(elsewhere, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_named_slugs_only(self):
        self.big("shop-a", 1000, 100, seed=1)
        self.big("shop-b", 1000, 100, seed=2)
        code, out = self.run_main("shop-b")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(os.listdir(self.folder)), ["shop-a.webp", "shop-b-800.webp", "shop-b.webp"])

    def test_a_name_with_no_shot_is_a_problem_and_writes_nothing_for_it(self):
        self.big("shop-a", 1000, 100)
        for name in ("no-such-shop", "../shop-a", "shop-a-800", "shop-a.webp"):
            with self.subTest(name=name):
                code, out = self.run_main(name)
                self.assertEqual(code, 1, out)
                self.assertIn("no desktop shot named", out)
                self.assertEqual(os.listdir(self.folder), ["shop-a.webp"])

    def test_a_broken_big_file_is_a_problem_and_the_others_are_still_made(self):
        self.big("shop-a", 1000, 100)
        with open(os.path.join(self.folder, "broken.webp"), "wb") as f:
            f.write(b"not a picture")
        code, out = self.run_main()
        self.assertEqual(code, 1, out)
        self.assertIn("work/shots/desktop/broken.webp cannot be read as WebP", out)
        self.assertEqual(sorted(os.listdir(self.folder)), ["broken.webp", "shop-a-800.webp", "shop-a.webp"])

    def test_steps_the_quality_down_to_fit_the_size_cap(self):
        self.big("test-shop", 1200, 750)
        real = ms.SMALL_MAX_BYTES
        self.addCleanup(setattr, ms, "SMALL_MAX_BYTES", real)
        self.assertEqual(self.run_main()[0], 0)
        at_82 = len(self.data("test-shop-800"))
        ms.SMALL_MAX_BYTES = at_82 - 1
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertLess(len(self.data("test-shop-800")), at_82)
        self.assertNotIn("q82", out)
        ms.SMALL_MAX_BYTES = 1
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("q70", out)
        self.assertIn("OVER", out)
        self.assertEqual(self.size("test-shop-800"), (800, 500))

    def test_without_the_webp_tools_it_stops_and_writes_nothing(self):
        self.big("test-shop", 1000, 100)
        real = ms.find_tools
        ms.find_tools = lambda: None
        try:
            code, out = self.run_main()
        finally:
            ms.find_tools = real
        self.assertEqual(code, 2, out)
        self.assertIn("needs dwebp and cwebp", out)
        self.assertEqual(os.listdir(self.folder), ["test-shop.webp"])

    def test_the_build_offers_the_copy_this_script_made(self):
        # end to end: a card whose shot got a copy from this script gets srcset on /work/
        with open(os.path.join(self.root, "index.html"), "w", encoding="utf-8") as f:
            f.write('<a href="/work/">Sample designs</a>')
        for path, text in (("_tools/templates/work.html", "<!doctype html><title>Sample designs</title><ul>{{CARDS}}</ul>\n"),
                           ("designs/test-shop/index.html", '<!doctype html><html><head><title>Test Shop</title>'
                            '<meta name="robots" content="noindex, follow"></head><body><h1>Test Shop</h1></body></html>'),
                           ("_tools/data/designs.json", '[{"slug": "test-shop", "name": "Test Shop", "trade": "Roofing", '
                            '"town": "Testville", "state": "NC"}]'),
                           ("_tools/data/designs.private.json", '{"test-shop": {"real": "real-shop"}}'),
                           ("samples/real-shop/index.html", '<!doctype html><html><head><title>Real Shop</title>'
                            '<meta name="robots" content="noindex"></head><body>x</body></html>')):
            full = os.path.join(self.root, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(text)
        self.big("test-shop", 1200, 750)
        self.assertEqual(self.run_main()[0], 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bp.main(["--no-shots"])
        self.assertEqual(code, 0, out.getvalue())
        with open(os.path.join(self.root, "work", "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('srcset="/work/shots/desktop/test-shop-800.webp 800w, /work/shots/desktop/test-shop.webp 1200w" '
                      'sizes="(max-width: 599px) 93vw, 801px"', page)


if __name__ == "__main__":
    unittest.main()
