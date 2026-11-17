"""Tests for build_pages.py. Every test builds a small made up site in a temp folder; the real site is never
written. Only the Tracked tests read it (the tracked designs.json and .gitignore), and they print no values.
Run from the site folder:  python3 -m unittest discover -s _tools -p "test_*.py"
"""
import contextlib
import html
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402

REAL_ROOT = bp.ROOT
TEMPLATE = "<!doctype html><title>Sample designs</title><ul>{{CARDS}}</ul>\n"
# The test phone uses area code 555, which is not assigned to anyone. It is not a 555-01xx number on purpose:
# the leak check skips numbers whose middle three digits are 555 (placeholders), so one of those would not test it.
PAGE = ('<!doctype html><html><head><title>Acme Roof Pros LLC | Roofing in Testville, NC</title>'
        '<meta name="robots" content="noindex"></head><body><a href="tel:+15554040123">(555) 404-0123</a></body></html>')
NOINDEX = '<meta name="robots" content="noindex, follow">'
DESIGN = ('<!doctype html><html><head><title>Bluebird Roofing | Roofing in Testville, NC</title>' + NOINDEX +
          '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Sample"}</script></head>'
          '<body><h1>Bluebird Roofing</h1><a href="tel:+13365550101">(336) 555-0101</a>'
          '<img src="../../samples/mark/gcd-mark-still.webp"></body></html>')


def with_ld(ld_text):
    """The design page with one more JSON-LD block in its head."""
    return DESIGN.replace("</head>", '<script type="application/ld+json">%s</script></head>' % ld_text)
ENTRY = {"real": "acme-roof-pros", "slug": "bluebird-roofing", "name": "Bluebird Roofing",
         "trade": "Roofing", "town": "Testville", "state": "NC"}


def put(root, relpath, text):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class SiteBase(unittest.TestCase):
    """A small made up site in a temp folder, and helpers. Holds no tests."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gcd-test-")
        bp.set_root(self.root)
        self.shipped_town_switch = bp.SHOW_SAMPLE_TOWN
        self.addCleanup(setattr, bp, "SHOW_SAMPLE_TOWN", self.shipped_town_switch)
        put(self.root, "index.html", '<a href="/work/">Sample designs</a>')
        put(self.root, "faq/index.html", "faq")
        put(self.root, "_tools/templates/work.html", TEMPLATE)
        put(self.root, "samples/acme-roof-pros/index.html", PAGE)
        put(self.root, "designs/bluebird-roofing/index.html", DESIGN)
        self.designs([ENTRY])

    def tearDown(self):
        bp.set_root(REAL_ROOT)
        shutil.rmtree(self.root, ignore_errors=True)

    def designs(self, items):
        """Write entries the way the site keeps them: public facts in designs.json, and "real" and
        "block" in designs.private.json keyed by the made up slug."""
        public = [{k: v for k, v in it.items() if k not in bp.PRIVATE_DESIGN_KEYS} for it in items]
        private = {it["slug"]: {k: it[k] for k in bp.PRIVATE_DESIGN_KEYS if k in it} for it in items}
        put(self.root, "_tools/data/designs.json", json.dumps(public))
        put(self.root, "_tools/data/designs.private.json", json.dumps(private))

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bp.main(list(args))
        return code, out.getvalue()

    def read(self, relpath):
        with open(os.path.join(self.root, relpath), encoding="utf-8") as f:
            return f.read()

    def town(self, on):
        """Set the SHOW_SAMPLE_TOWN switch for one test (setUp puts the shipped value back after)."""
        bp.SHOW_SAMPLE_TOWN = on


class Site(SiteBase):
    # ---- check

    def test_clean_site_passes_check(self):
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: OK", out)

    def test_real_name_in_design_fails(self):
        put(self.root, "designs/bluebird-roofing/about.html", "<p>Formerly Acme Roof Pros.</p>")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("acme roof pros", out)

    def test_real_name_split_by_tags_and_entities_fails(self):
        put(self.root, "designs/bluebird-roofing/a.html", "<b>ACME</b> Roof&nbsp;Pros")
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_real_phone_in_design_fails(self):
        put(self.root, "designs/bluebird-roofing/c.html", "Call 555.404.0123")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("phone number ending 0123", out)

    def test_real_slug_in_sitemap_fails(self):
        put(self.root, "sitemap.xml", "<loc>https://granitecitydigital.me/designs/acme-roof-pros/</loc>")
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_old_real_shot_file_name_fails(self):
        put(self.root, "work/shots/acme-roof-pros.webp", "x")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("work/shots/acme-roof-pros.webp", out)

    def test_block_list_name_fails(self):
        self.designs([dict(ENTRY, block=["Pat Example"])])
        put(self.root, "designs/bluebird-roofing/d.html", "Ask for Pat Example")
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_missing_noindex_fails(self):
        put(self.root, "samples/acme-roof-pros/index.html", PAGE.replace('<meta name="robots" content="noindex">', ""))
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("samples/acme-roof-pros/index.html", out)

    def test_public_links_to_samples_fail(self):
        for i, page in enumerate(['<a href="/samples/acme-roof-pros/">x</a>',
                                  '<a href="../samples/acme-roof-pros/">x</a>',
                                  '<script>var u = "/samples/" + slug;</script>',
                                  '<a href="https://granitecitydigital.me/web-design/">x</a>']):
            with self.subTest(page=page):
                put(self.root, "faq/index.html", page)
                code, out = self.run_main("--check")
                self.assertEqual(code, 1, out)
                self.assertIn("faq/index.html", out)

    def test_mark_folder_and_sample_page_are_allowed(self):
        put(self.root, "faq/index.html", '<img src="/samples/mark/gcd-mark-still.webp"><a href="/sample/">x</a>')
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_web_design_folder_fails(self):
        put(self.root, "web-design/index.html", "old")
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_design_without_noindex_fails(self):
        put(self.root, "designs/bluebird-roofing/index.html", DESIGN.replace(NOINDEX, ""))
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("Pages in designs/ without a noindex robots meta: 1", out)

    def test_design_folder_not_in_designs_json_still_needs_noindex(self):
        put(self.root, "designs/stray-shop/index.html", "<title>Stray</title>")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("designs/stray-shop/index.html", out)

    def test_design_business_structured_data_fails(self):
        cases = ['{"@context":"https://schema.org","@type":"LocalBusiness","name":"Bluebird Roofing"}',
                 '{"@type":"RoofingContractor"}',
                 '{"@type":["WebPage","Plumber"]}',
                 '{"@graph":[{"@type":"WebSite"},{"@type":"Restaurant"}]}',
                 '[{"@type":"WebPage"},{"@type":"https://schema.org/Electrician"}]',
                 '{"@type": "LocalBusiness", oops}']
        for ld in cases:
            with self.subTest(ld=ld):
                put(self.root, "designs/bluebird-roofing/index.html", with_ld(ld))
                code, out = self.run_main("--check")
                self.assertEqual(code, 1, out)
                self.assertIn("Business structured data on designs/ pages", out)
                self.assertIn("designs/bluebird-roofing/index.html: JSON-LD", out)

    def test_design_business_microdata_fails(self):
        put(self.root, "designs/bluebird-roofing/index.html",
            DESIGN.replace("<body>", '<body itemscope itemtype="https://schema.org/LocalBusiness">'))
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("microdata itemtype LocalBusiness", out)

    def test_design_plain_page_structured_data_passes(self):
        put(self.root, "designs/bluebird-roofing/index.html",
            with_ld('{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1}]}'))
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("Business structured data on designs/ pages (LocalBusiness style JSON-LD or microdata): none", out)

    def test_old_mark_links_fail(self):
        cases = [("samples/acme-roof-pros/index.html", PAGE, PAGE.replace("</body>", '<img src="../_mark/gcd-mark-still.webp"></body>')),
                 ("designs/bluebird-roofing/index.html", DESIGN, DESIGN.replace("samples/mark/", "samples/_mark/")),
                 ("samples/_template/index.html", None, '<source src="../_mark/gcd-mark-2s.webm">')]
        for relpath, original, text in cases:
            with self.subTest(path=relpath):
                put(self.root, relpath, text)
                code, out = self.run_main("--check")
                self.assertEqual(code, 1, out)
                self.assertIn("Old _mark/ links or folder in samples/ or designs/ (use mark/): 1", out)
                self.assertIn(relpath + ": line 1", out)
            if original is None:
                os.remove(os.path.join(self.root, relpath))
            else:
                put(self.root, relpath, original)

    def test_old_mark_folder_fails(self):
        put(self.root, "samples/_mark/notes.txt", "old")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("samples/_mark/ (folder on disk", out)

    def test_public_link_to_old_mark_folder_fails(self):
        put(self.root, "faq/index.html", '<img src="/samples/_mark/gcd-mark-still.webp">')
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("faq/index.html: /samples/_mark/gcd-mark-still.webp", out)

    def test_gcd_mark_names_are_not_old_mark_links(self):
        put(self.root, "samples/acme-roof-pros/index.html",
            PAGE.replace("</body>", '<div class="gcd_mark/x"></div><img src="../mark/gcd-mark-still.webp"></body>'))
        code, out = self.run_main("--check")
        self.assertIn("Old _mark/ links or folder in samples/ or designs/ (use mark/): none", out)

    def test_sitemap_on_disk_listing_designs_fails(self):
        put(self.root, "sitemap.xml", "<loc>https://granitecitydigital.me/</loc>"
                                      "<loc>https://granitecitydigital.me/designs/bluebird-roofing/</loc>")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("sitemap.xml lists noindex designs/ pages", out)

    def test_public_slug_must_be_made_up(self):
        self.designs([dict(ENTRY, slug="acme-roof-pros")])
        self.assertEqual(self.run_main("--check")[0], 2)

    # ---- private file

    def test_missing_private_file_stops_check_and_build(self):
        os.remove(os.path.join(self.root, "_tools/data/designs.private.json"))
        for args in (("--check",), ("--no-shots",)):
            with self.subTest(args=args):
                code, out = self.run_main(*args)
                self.assertEqual(code, 2, out)
                self.assertIn("designs.private.json is missing", out)
                self.assertFalse(os.path.exists(os.path.join(self.root, "work")))
                self.assertFalse(os.path.exists(os.path.join(self.root, "sitemap.xml")))

    def test_empty_list_needs_no_private_file(self):
        self.designs([])
        os.remove(os.path.join(self.root, "_tools/data/designs.private.json"))
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_private_fields_in_tracked_file_fail(self):
        for key, value in (("real", "acme-roof-pros"), ("block", ["Pat Example"])):
            with self.subTest(key=key):
                public = {k: v for k, v in ENTRY.items() if k != "real"}
                public[key] = value
                put(self.root, "_tools/data/designs.json", json.dumps([public]))
                code, out = self.run_main("--check")
                self.assertEqual(code, 2, out)
                self.assertIn("move them to _tools/data/designs.private.json", out)

    def test_private_file_must_match_designs_json(self):
        public = [{k: v for k, v in ENTRY.items() if k != "real"}]
        # a design with no private entry, an extra entry, a field that is not private, not an object
        cases = [{},
                 {"bluebird-roofing": {"real": "acme-roof-pros"}, "other-shop": {"real": "x"}},
                 {"bluebird-roofing": {"real": "acme-roof-pros", "name": "x"}},
                 ["acme-roof-pros"]]
        for private in cases:
            with self.subTest(private=private):
                put(self.root, "_tools/data/designs.json", json.dumps(public))
                put(self.root, "_tools/data/designs.private.json", json.dumps(private))
                code, out = self.run_main("--check")
                self.assertEqual(code, 2, out)
                self.assertIn("designs.private.json", out)

    def test_block_words_from_private_file_are_scanned(self):
        self.designs([dict(ENTRY, block=["Pat Example"])])
        self.assertNotIn("Pat Example", self.read("_tools/data/designs.json"))
        put(self.root, "designs/bluebird-roofing/e.html", "Ask for Pat Example")
        self.assertEqual(self.run_main("--check")[0], 1)

    # ---- photos reused from samples/

    def put_bytes(self, relpath, data):
        path = os.path.join(self.root, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def test_design_image_same_bytes_as_a_lead_image_fails(self):
        self.put_bytes("samples/acme-roof-pros/hero.jpg", b"\xff\xd8 page photo one")
        self.put_bytes("designs/bluebird-roofing/roof.jpg", b"\xff\xd8 page photo one")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("designs/bluebird-roofing/roof.jpg: same bytes as samples/acme-roof-pros/hero.jpg", out)

    def test_sample_page_image_same_bytes_as_a_lead_image_fails(self):
        self.put_bytes("samples/acme-roof-pros/steps.webp", b"RIFF page photo two")
        self.put_bytes("sample/img/steps-640.webp", b"RIFF page photo two")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("sample/img/steps-640.webp: same bytes as samples/acme-roof-pros/steps.webp", out)

    def test_different_image_bytes_with_the_same_name_pass(self):
        self.put_bytes("samples/acme-roof-pros/hero.jpg", b"\xff\xd8 page photo one")
        self.put_bytes("designs/bluebird-roofing/hero.jpg", b"\xff\xd8 another photo")
        self.put_bytes("sample/img/hero.jpg", b"\xff\xd8 a third photo")
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)

    def test_same_bytes_in_a_non_image_file_pass(self):
        self.put_bytes("samples/acme-roof-pros/notes.txt", b"same words")
        self.put_bytes("designs/bluebird-roofing/notes.txt", b"same words")
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_copy_of_the_shared_mark_passes(self):
        self.put_bytes("samples/mark/gcd-mark-still.png", b"\x89PNG our own mark")
        self.put_bytes("designs/bluebird-roofing/mark.png", b"\x89PNG our own mark")
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_photo_ids_from_credit_text(self):
        text = ("hero.jpg  Source: https://www.pexels.com/photo/man-on-a-ladder-1234567/\n"
                "steps.jpg https://www.pexels.com/photo/7654321/ and https://www.pexels.com/es-es/photo/2468024/\n"
                "big.jpg https://images.pexels.com/photos/1357913/pexels-photo-1357913.jpeg?w=640\n"
                "a.jpg https://unsplash.com/photos/red-roof-on-a-barn-Ab3dE_f9-Xz\n"
                "b.jpg https://unsplash.com/photos/Qq1Ww2Ee3Rr\n"
                "Photographer: https://www.pexels.com/@someone-5550000/ License: https://www.pexels.com/license/\n"
                "License: https://unsplash.com/license\n")
        self.assertEqual(bp.photo_ids(text), {"Pexels photo 1234567", "Pexels photo 7654321", "Pexels photo 2468024",
                                              "Pexels photo 1357913", "Unsplash photo Ab3dE_f9-Xz",
                                              "Unsplash photo Qq1Ww2Ee3Rr"})

    def test_pexels_id_in_design_credits_and_lead_credits_fails(self):
        put(self.root, "samples/acme-roof-pros/photo-credits.txt", "hero.jpg https://www.pexels.com/photo/1234567/\n")
        put(self.root, "designs/bluebird-roofing/photo-credits.txt",
            "roof.jpg https://www.pexels.com/photo/man-on-a-ladder-1234567/\n")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("designs/bluebird-roofing/photo-credits.txt: Pexels photo 1234567, also in "
                      "samples/acme-roof-pros/photo-credits.txt", out)

    def test_unsplash_id_in_sample_page_credits_and_lead_credits_fails(self):
        put(self.root, "samples/acme-roof-pros/photo-credits.txt", "https://unsplash.com/photos/red-roof-Ab3dE_f9-Xz\n")
        put(self.root, "sample/photo-credits.txt", "https://unsplash.com/photos/Ab3dE_f9-Xz\n")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("sample/photo-credits.txt: Unsplash photo Ab3dE_f9-Xz", out)

    def test_different_photo_ids_pass(self):
        put(self.root, "samples/acme-roof-pros/photo-credits.txt",
            "https://www.pexels.com/photo/1234567/\nhttps://unsplash.com/photos/Ab3dE_f9-Xz\n")
        put(self.root, "designs/bluebird-roofing/photo-credits.txt",
            "https://www.pexels.com/photo/12345678/\nhttps://www.pexels.com/photo/234567/\n"
            "https://unsplash.com/photos/ab3de_f9-xz\n")
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)

    def test_build_stops_on_a_reused_photo_and_writes_nothing(self):
        self.put_bytes("samples/acme-roof-pros/hero.jpg", b"\xff\xd8 page photo one")
        self.put_bytes("designs/bluebird-roofing/hero.jpg", b"\xff\xd8 page photo one")
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 1, out)
        self.assertIn("STOPPED", out)
        self.assertIn("designs/bluebird-roofing/hero.jpg: same bytes as samples/acme-roof-pros/hero.jpg", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "sitemap.xml")))

    def test_build_stops_on_a_reused_photo_id_and_writes_nothing(self):
        put(self.root, "samples/acme-roof-pros/photo-credits.txt", "https://www.pexels.com/photo/1234567/\n")
        put(self.root, "designs/bluebird-roofing/photo-credits.txt", "https://www.pexels.com/photo/1234567/\n")
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 1, out)
        self.assertIn("STOPPED", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))

    # ---- build

    def test_build_writes_only_fake_names(self):
        put(self.root, "work/shots/acme-roof-pros.webp", "old")
        put(self.root, "work/shots/keep-me.webp", "other")
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page, data, sitemap = self.read("work/index.html"), self.read("work/samples.json"), self.read("sitemap.xml")
        self.assertIn("Bluebird Roofing", page)
        self.assertIn('href="/designs/bluebird-roofing/"', page)
        for text in (page, data, sitemap):
            self.assertNotIn("acme", text.lower())
            self.assertNotIn("/samples/", text)
        self.assertEqual(json.loads(data)[0]["slug"], "bluebird-roofing")
        self.assertNotIn("real", json.loads(data)[0])
        self.assertFalse(os.path.exists(os.path.join(self.root, "work/shots/acme-roof-pros.webp")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "work/shots/keep-me.webp")))
        self.assertNotIn("/designs/", sitemap)          # design pages are noindex; /work/ links them
        self.assertIn("/work/", sitemap)
        self.assertIn("/faq/", sitemap)
        self.assertNotIn("/privacy/", sitemap)          # no page on disk, left out

    def test_build_stops_on_leak_and_writes_nothing(self):
        put(self.root, "designs/bluebird-roofing/index.html", DESIGN.replace("Bluebird Roofing</h1>", "Acme Roof Pros</h1>"))
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 1)
        self.assertIn("STOPPED", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "sitemap.xml")))

    def test_build_with_empty_list_writes_nothing(self):
        self.designs([])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))

    def test_alt_text_uses_a_business_noun(self):
        self.town(True)
        self.designs([dict(ENTRY, trade="Lawn maintenance")])
        put(self.root, "designs/bluebird-roofing/index.html", with_ld('{"@type":"HomeAndConstructionBusiness"}'))
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn('alt="Desktop view of a sample design for a lawn care business in Testville"', page)
        self.assertNotIn("home repair business", page)
        self.assertNotIn("a lawn maintenance in", page)

    def test_alt_text_ignores_plain_page_types(self):
        self.town(True)
        self.designs([dict(ENTRY, trade="Pet grooming")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn("for a pet grooming business in Testville", page)
        self.assertNotIn("web page", page)

    # ---- alt text nouns (no files)

    def test_alt_nouns(self):
        vague = "HomeAndConstructionBusiness"
        cases = [
            ("Lawn maintenance", vague, "lawn care business"),
            ("Tree service", vague, "tree service"),
            ("Landscaping, hardscaping and outdoor living", vague, "landscaper"),
            ("Pressure washing", vague, "pressure washing business"),
            ("Seamless gutters, roofing and siding", vague, "gutter business"),
            ("Concrete and grading", "GeneralContractor", "concrete contractor"),
            ("Diner on Main Street", "Restaurant", "diner"),
            ("Sandwiches", "Restaurant", "sandwich shop"),
            ("Esthetics studio", "BeautySalon", "esthetics studio"),
            ("Window washing", vague, "window washing business"),
            ("Chimney sweeping", "", "chimney sweeping business"),
            ("Pet grooming", "LocalBusiness", "pet grooming business"),
        ]
        for trade, page_type, want in cases:
            with self.subTest(trade=trade):
                self.assertEqual(bp.alt_noun("made-up-real", trade, page_type), want)
        self.assertEqual(bp.article("HVAC company"), "an")
        self.assertEqual(bp.article("esthetics studio"), "an")

    def test_alt_nouns_for_food_shops_and_offices(self):
        # trades with no business JSON-LD on the page must still read as a kind of business
        cases = [
            ("Coffee and doughnuts", "coffee shop"),
            ("Sandwiches", "sandwich shop"),
            ("Southern breakfast and lunch", "breakfast restaurant"),
            ("Burgers on Main Street", "burger shop"),
            ("Burger shop", "burger shop"),
            ("Diner", "diner"),
            ("Auto body, paint and tires", "auto body shop"),
            ("Auto repair", "auto repair shop"),
            ("Auto repair, A/C repair and inspections", "auto repair shop"),
            ("Tax preparer", "tax service"),
            ("House painting", "house painter"),
            ("Skin care", "skin care studio"),
        ]
        for trade, want in cases:
            with self.subTest(trade=trade):
                self.assertEqual(bp.alt_noun("made-up-real", trade, ""), want)

    def test_alt_text_on_the_card_for_a_food_trade(self):
        self.town(True)
        self.designs([dict(ENTRY, trade="Sandwiches")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn('alt="Desktop view of a sample design for a sandwich shop in Testville"', page)
        self.assertNotIn("sandwiches business", page)

    # ---- card markup

    def test_card_has_three_tags_line_and_browser_frame(self):
        self.town(True)
        self.designs([dict(ENTRY, line="A bold website for a Testville roofer.")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn('<div class="tag-row"><span class="tag tag-sample">Sample design</span>'
                      '<span class="tag">Roofing</span><span class="tag">Testville, NC</span></div>', page)
        self.assertIn("<h2>Bluebird Roofing</h2>", page)
        self.assertIn('<p class="card-line">A bold website for a Testville roofer.</p>', page)
        self.assertIn('<div class="frame"><div class="frame-bar"><span></span><span></span><span></span>'
                      '<span class="frame-url">granitecitydigital.me/designs/bluebird-roofing/</span></div><img ', page)
        self.assertIn('<li class="work-card feature">', page)       # no featured.json: the first design leads
        self.assertIn('<a class="link" href="/designs/bluebird-roofing/"', page)
        self.assertNotIn("Roofing in Testville, NC</p>", page)      # the old trade line is gone

    def test_card_frame_shows_the_desktop_shot(self):
        self.town(True)
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        # the only design leads (no featured.json), so its picture is on the first screen: not lazy
        self.assertIn('<img src="/work/shots/desktop/bluebird-roofing.webp" '
                      'alt="Desktop view of a sample design for a roofer in Testville" width="1200" height="750" '
                      'decoding="async"></div>', page)
        self.assertNotIn('loading="lazy"', page)
        self.assertNotIn('src="/work/shots/bluebird-roofing.webp"', page)
        # samples.json (read by the free check) keeps the phone shot
        self.assertEqual(json.loads(self.read("work/samples.json"))[0]["shot"], "/work/shots/bluebird-roofing.webp")
        # the card alt names the desktop shot; samples.json keeps the phone alt for the free check
        self.assertNotIn('alt="Phone view of', page)
        self.assertEqual(json.loads(self.read("work/samples.json"))[0]["alt"],
                         "Phone view of a sample design for a roofer in Testville")
        self.assertNotIn("desktop_alt", self.read("work/samples.json"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "work/shots/desktop")))

    # ---- which shots the build asks for (Chrome is never started here)

    def shots_asked(self, *args):
        asked = []
        real = bp.take_shots
        bp.take_shots = lambda phone, desktop=(), pages=None: asked.append((list(phone), list(desktop))) or []
        try:
            code, out = self.run_main(*args)
        finally:
            bp.take_shots = real
        self.assertEqual(code, 0, out)
        return asked

    def test_build_takes_missing_desktop_shots_only(self):
        self.assertEqual(self.shots_asked(), [(["bluebird-roofing"], ["bluebird-roofing"])])
        put(self.root, "work/shots/bluebird-roofing.webp", "phone")
        self.assertEqual(self.shots_asked(), [([], ["bluebird-roofing"])])
        put(self.root, "work/shots/desktop/bluebird-roofing.webp", "desktop")
        self.assertEqual(self.shots_asked(), [([], [])])
        self.assertEqual(self.shots_asked("--shots"), [(["bluebird-roofing"], ["bluebird-roofing"])])
        self.assertEqual(self.shots_asked("--no-shots"), [])

    def test_check_notes_a_missing_desktop_shot(self):
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("work/shots/desktop/bluebird-roofing.webp", out)
        put(self.root, "work/shots/desktop/bluebird-roofing.webp", "desktop")
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("work/shots/desktop/bluebird-roofing.webp", out)

    def test_build_notes_a_missing_desktop_shot(self):
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        self.assertIn("no desktop shot yet for bluebird-roofing", out)

    def test_card_line_falls_back_when_missing(self):
        self.town(True)
        self.designs([dict(ENTRY, trade="Tree service")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn('<p class="card-line">A sample website for a Testville tree service.</p>', page)

    def test_card_line_falls_back_when_blank(self):
        self.town(True)
        self.designs([dict(ENTRY, line="   ")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        self.assertIn('<p class="card-line">A sample website for a Testville roofing.</p>', self.read("work/index.html"))

    # ---- town switch (SHOW_SAMPLE_TOWN): off keeps where a sample is set off /work/

    def test_town_off_card_shows_no_town_or_state(self):
        self.town(False)
        self.designs([dict(ENTRY, line="A bold website for a Testville roofer.")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page, data = self.read("work/index.html"), self.read("work/samples.json")
        self.assertIn('<div class="tag-row"><span class="tag tag-sample">Sample design</span>'
                      '<span class="tag">Roofing</span></div>', page)
        self.assertIn('<p class="card-line">A bold website for a roofer.</p>', page)
        self.assertIn('alt="Desktop view of a sample design for a roofer"', page)
        self.assertIn('aria-label="Preview the sample design for Bluebird Roofing, a roofer"', page)
        self.assertEqual(json.loads(data), [{"slug": "bluebird-roofing", "name": "Bluebird Roofing", "trade": "Roofing",
                                             "alt": "Phone view of a sample design for a roofer",
                                             "shot": "/work/shots/bluebird-roofing.webp",
                                             "preview": "/designs/bluebird-roofing/"}])
        for text in (page, data):
            self.assertNotIn("testville", text.lower())
            self.assertNotRegex(text, r"\bNC\b")
        # the design page and designs.json keep the town
        self.assertIn("Testville", self.read("designs/bluebird-roofing/index.html"))
        self.assertEqual(json.loads(self.read("_tools/data/designs.json"))[0]["town"], "Testville")

    def test_town_on_brings_the_town_back(self):
        self.town(True)
        self.designs([dict(ENTRY, line="A bold website for a Testville roofer.")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page, data = self.read("work/index.html"), json.loads(self.read("work/samples.json"))
        self.assertIn('<span class="tag">Testville, NC</span>', page)
        self.assertIn('<p class="card-line">A bold website for a Testville roofer.</p>', page)
        self.assertIn('aria-label="Preview the sample design for Bluebird Roofing, a roofer in Testville"', page)
        self.assertEqual((data[0]["town"], data[0]["state"]), ("Testville", "NC"))
        self.assertEqual(data[0]["alt"], "Phone view of a sample design for a roofer in Testville")

    def test_town_off_fallback_line_names_the_kind_only(self):
        self.town(False)
        for line in (None, "   "):
            with self.subTest(line=line):
                entry = dict(ENTRY, trade="Tree service")
                if line is not None:
                    entry["line"] = line
                self.designs([entry])
                code, out = self.run_main("--no-shots")
                self.assertEqual(code, 0, out)
                self.assertIn('<p class="card-line">A sample website for a tree service.</p>', self.read("work/index.html"))

    def test_town_free_line(self):
        cases = [
            ("A clean website for a Testville tree service.", "Testville", "tree service",
             "A clean website for a tree service."),
            ("A sturdy website for a Mount Airy auto body and tire shop.", "Mount Airy", "auto body shop",
             "A sturdy website for an auto body and tire shop."),
            ("A calm website for an Elkin esthetics studio.", "Elkin", "esthetics studio",
             "A calm website for an esthetics studio."),
            ("A website for an Oak Hill bakery.", "Oak Hill", "bakery", "A website for a bakery."),
            ("A website for a Testville, NC roofer.", "Testville", "roofer", "A website for a roofer."),
            ("A website for a TESTVILLE roofer.", "Testville", "roofer", "A website for a roofer."),
            ("A friendly website for a plumber in Testville, NC.", "Testville", "plumber",
             "A friendly website for a plumber."),
            ("A website for a roofer from Testville.", "Testville", "roofer", "A website for a roofer."),
            ("A website for a Testville stone mason who builds patios, walls and steps.", "Testville", "stone mason",
             "A website for a stone mason who builds patios, walls and steps."),
            ("A bold website for a roofer.", "Testville", "roofer", "A bold website for a roofer."),
            ("A website for an Elkin roofer.", "Elk", "roofer", "A website for an Elkin roofer."),
            # the town anywhere else, or the state left alone: the plain line instead
            ("Testville's favorite roofer.", "Testville", "roofer", "A sample website for a roofer."),
            ("Testville roofing, done right.", "Testville", "roofer", "A sample website for a roofer."),
            ("The best roofer in NC.", "Testville", "roofer", "A sample website for a roofer."),
            ("Serving Testville and nearby towns.", "Testville", "HVAC company", "A sample website for an HVAC company."),
        ]
        for line, town, kind, want in cases:
            with self.subTest(line=line):
                self.assertEqual(bp.town_free_line(line, town, "NC", kind), want)

    def test_town_off_check_flags_a_town_left_in_the_cards(self):
        self.town(False)
        self.designs([dict(ENTRY, name="Testville Roofing")])
        code, out = self.run_main("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("Sample towns or states still on /work/ with SHOW_SAMPLE_TOWN off: 1", out)
        self.assertIn("Testville", out)
        self.town(True)
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("Sample towns or states still on", out)

    def test_town_off_clean_site_passes_check(self):
        self.town(False)
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("Sample towns or states still on /work/ with SHOW_SAMPLE_TOWN off: none", out)

    def test_card_text_is_escaped(self):
        self.designs([dict(ENTRY, name="Bluebird & Sons", trade="Roofing & <b>gutters</b>",
                           line='A "bold" website & more <i>.')])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn("<h2>Bluebird &amp; Sons</h2>", page)
        self.assertIn('<span class="tag">Roofing &amp; &lt;b&gt;gutters&lt;/b&gt;</span>', page)
        self.assertIn('<p class="card-line">A &quot;bold&quot; website &amp; more &lt;i&gt;.</p>', page)
        self.assertNotIn("<b>gutters", page)

    def test_sitemap_only(self):
        code, _ = self.run_main("--sitemap")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))
        sitemap = self.read("sitemap.xml")
        self.assertNotIn("/designs/", sitemap)
        self.assertIn("<loc>https://granitecitydigital.me/faq/</loc>", sitemap)
        # the sitemap it writes passes its own check
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_sitemap_page_list_and_order(self):
        self.assertEqual(bp.SITEMAP_PAGES, [
            "/", "/services/website-design/", "/services/website-rebuild/", "/services/care-plan/",
            "/services/free-website-check/", "/services/google-business-profile/", "/services/local-seo/",
            "/services/logo-and-brand-kit/", "/websites-for/home-services/", "/websites-for/auto-shops/",
            "/websites-for/food-and-coffee/", "/websites-for/beauty-and-wellness/", "/work/", "/sample/", "/about/",
            "/contact/", "/faq/", "/service-area/", "/get-started/", "/free-check/", "/privacy/", "/terms/"])

    def test_sitemap_lists_get_started_but_not_client_portal(self):
        for p in ("/get-started/", "/client-portal/"):
            put(self.root, p.strip("/") + "/index.html", "x")
        self.assertIn("/get-started/", bp.SITEMAP_PAGES)
        self.assertNotIn("/client-portal/", bp.SITEMAP_PAGES)
        self.assertEqual(self.run_main("--sitemap")[0], 0)
        sitemap = self.read("sitemap.xml")
        self.assertIn("<loc>https://granitecitydigital.me/get-started/</loc>", sitemap)
        self.assertNotIn("/client-portal/", sitemap)

    def test_sitemap_lists_new_service_and_trade_pages_on_disk_only(self):
        for p in ("services/website-design", "services/free-website-check", "services/local-seo",
                  "websites-for/auto-shops", "websites-for/beauty-and-wellness", "work"):
            put(self.root, p + "/index.html", "x")
        code, out = self.run_main("--sitemap")
        self.assertEqual(code, 0, out)
        locs = [ln.split("<loc>")[1].split("</loc>")[0] for ln in self.read("sitemap.xml").splitlines() if "<loc>" in ln]
        base = "https://granitecitydigital.me"
        self.assertEqual(locs, [base + p for p in (
            "/", "/services/website-design/", "/services/free-website-check/", "/services/local-seo/",
            "/websites-for/auto-shops/", "/websites-for/beauty-and-wellness/", "/work/", "/faq/")])
        for p in ("/services/google-business-profile/", "/websites-for/home-services/"):
            self.assertIn("left out, no page on disk yet: " + p, out)

    def test_check_notes_a_sitemap_page_that_is_noindex(self):
        put(self.root, "get-started/index.html", '<head><meta name="robots" content="noindex"></head>')
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("Note: sitemap pages that still carry a noindex robots meta: 1", out)
        self.assertIn("  /get-started/", out)
        put(self.root, "get-started/index.html", "<head></head>")
        code, out = self.run_main("--check")
        self.assertIn("Note: sitemap pages that still carry a noindex robots meta: none", out)

    def test_sitemap_lists_about_after_sample(self):
        for p in ("work", "sample", "about"):
            put(self.root, p + "/index.html", "x")
        self.assertEqual(self.run_main("--sitemap")[0], 0)
        locs = [ln.split("<loc>")[1].split("</loc>")[0] for ln in self.read("sitemap.xml").splitlines() if "<loc>" in ln]
        base = "https://granitecitydigital.me"
        self.assertEqual(locs, [base + "/", base + "/work/", base + "/sample/", base + "/about/", base + "/faq/"])
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_sitemap_lists_service_pages_in_order(self):
        for p in ("services/care-plan", "services/website-design", "work"):
            put(self.root, p + "/index.html", "x")
        self.assertEqual(self.run_main("--sitemap")[0], 0)
        locs = [ln.split("<loc>")[1].split("</loc>")[0] for ln in self.read("sitemap.xml").splitlines() if "<loc>" in ln]
        base = "https://granitecitydigital.me"
        self.assertEqual(locs, [base + "/", base + "/services/website-design/", base + "/services/care-plan/",
                                base + "/work/", base + "/faq/"])

    def test_real_name_or_phone_in_new_folders_fails(self):
        for folder in ("services/care-plan", "get-started", "client-portal", "about", "websites-for/home-services",
                       "contact", "faq", "free-check", "privacy", "terms", "service-area"):
            for text, want in (("<p>Formerly Acme Roof Pros.</p>", "acme roof pros"),
                               ("Call 555.404.0123", "phone number ending 0123")):
                with self.subTest(folder=folder, text=text):
                    put(self.root, folder + "/index.html", text)
                    code, out = self.run_main("--check")
                    os.remove(os.path.join(self.root, folder, "index.html"))
                    self.assertEqual(code, 1, out)
                    self.assertIn(folder + "/index.html: ", out)
                    self.assertIn(want, out)

    def test_real_name_or_phone_in_root_pages_fails(self):
        for name in ("index.html", "404.html"):
            for text, want in (("<p>Formerly Acme Roof Pros.</p>", "acme roof pros"),
                               ("Call 555.404.0123", "phone number ending 0123"),
                               ('<img src="/work/shots/acme-roof-pros.webp">', "private slug acme-roof-pros")):
                with self.subTest(name=name, text=text):
                    put(self.root, name, text)
                    code, out = self.run_main("--check")
                    os.remove(os.path.join(self.root, name))
                    self.assertEqual(code, 1, out)
                    self.assertIn("\n  %s: " % name, out)
                    self.assertIn(want, out)

    def test_root_scan_skips_samples_and_tool_folders(self):
        # the lead pages carry their own names and phones; the root scan covers only the two root pages
        put(self.root, "samples/acme-roof-pros/about.html", NOINDEX + "<p>Acme Roof Pros. Call 555.404.0123</p>")
        put(self.root, "_tools/notes.md", "acme-roof-pros is Acme Roof Pros")
        put(self.root, "index.html", '<a href="/work/">Sample designs</a>')
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("index.html, 404.html", out)


def put_bytes(root, relpath, data):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def png_head(w, h):
    """The first bytes of a PNG file of w x h: enough for the size reader."""
    return (b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR" + w.to_bytes(4, "big") + h.to_bytes(4, "big")
            + b"\x08\x02\x00\x00\x00" + b"\x00" * 4)


FEATURE = {"page": "/sample/", "shot": "granite-ridge-test", "image": "/sample/card.png",
           "name": "Granite Ridge Masonry", "trade": "Stone mason", "town": "Testville", "state": "NC",
           "line": "A website for a Testville stone mason who builds patios, walls and steps."}
FEATURE_PAGE = '<!doctype html><html><head><title>Granite Ridge Masonry | Sample</title></head><body>x</body></html>'


class Feature(SiteBase):
    """The feature card (_tools/data/featured.json): a made up sample page outside designs/, shown first and wide."""

    def setUp(self):
        super().setUp()
        put(self.root, "sample/index.html", FEATURE_PAGE)
        put_bytes(self.root, "sample/card.png", png_head(1000, 800))
        self.feature(FEATURE)

    def feature(self, data):
        put(self.root, "_tools/data/featured.json", json.dumps(data))

    def build(self, *args):
        code, out = self.run_main("--no-shots", *args)
        self.assertEqual(code, 0, out)
        return self.read("work/index.html"), out

    def test_feature_card_comes_first_with_tags_line_and_link(self):
        self.town(True)
        page, _ = self.build()
        first = page.index('<li class="work-card feature">')
        self.assertLess(first, page.index('<li class="work-card', first + 1))
        card = page[first:page.index("</li>", first)]
        self.assertIn('<div class="tag-row"><span class="tag tag-sample">Sample design</span>'
                      '<span class="tag">Stone mason</span><span class="tag">Testville, NC</span></div>', card)
        self.assertIn("<h2>Granite Ridge Masonry</h2>", card)
        self.assertIn('<p class="card-line">A website for a Testville stone mason who builds patios, walls and steps.</p>',
                      card)
        self.assertIn('<span class="frame-url">granitecitydigital.me/sample/</span>', card)
        self.assertIn('<a class="link" href="/sample/" target="_blank" rel="noopener" aria-label="Preview the sample '
                      'design for Granite Ridge Masonry, a stone mason in Testville">Preview</a>', card)
        # the design card after it is a plain card, not the feature
        self.assertEqual(page.count("work-card feature"), 1)
        self.assertIn('href="/designs/bluebird-roofing/"', page)

    def test_town_off_feature_card_shows_no_town_or_state(self):
        self.town(False)
        page, _ = self.build()
        first = page.index('<li class="work-card feature">')
        card = page[first:page.index("</li>", first)]
        self.assertIn('<div class="tag-row"><span class="tag tag-sample">Sample design</span>'
                      '<span class="tag">Stone mason</span></div>', card)
        self.assertIn('<p class="card-line">A website for a stone mason who builds patios, walls and steps.</p>', card)
        self.assertIn('alt="Desktop view of a sample design for a stone mason"', card)
        self.assertIn('aria-label="Preview the sample design for Granite Ridge Masonry, a stone mason"', card)
        self.assertNotIn("Testville", page)
        self.assertNotRegex(page, r"\bNC\b")
        self.assertEqual(json.loads(self.read("_tools/data/featured.json"))["town"], "Testville")

    def test_feature_uses_its_page_image_until_a_desktop_shot_exists(self):
        self.town(True)
        page, _ = self.build()
        self.assertIn('<img src="/sample/card.png" alt="Desktop view of a sample design for a stone mason in Testville" '
                      'width="1000" height="800" decoding="async">', page)
        put(self.root, "work/shots/desktop/granite-ridge-test.webp", "desktop")
        page, _ = self.build()
        self.assertIn('<img src="/work/shots/desktop/granite-ridge-test.webp" alt="Desktop view of a sample design for '
                      'a stone mason in Testville" width="1200" height="750"', page)
        self.assertNotIn("/sample/card.png", page)

    def test_only_the_lead_card_picture_is_not_lazy(self):
        # the lead card (the feature, or the first design with no featured.json) is on the first screen,
        # so its picture loads right away; every other card picture stays lazy
        entries = [dict(ENTRY, real="real-shop-%d" % i, slug="test-shop-%d" % i, name="Test Shop %d" % i)
                   for i in range(1, 4)]
        for e in entries:
            put(self.root, "designs/%s/index.html" % e["slug"], DESIGN)
        shutil.rmtree(os.path.join(self.root, "designs", "bluebird-roofing"))
        self.designs(entries)
        lead_img = r'<img src="[^"]+" alt="[^"]+" width="\d+" height="\d+" decoding="async">'
        lazy_img = r'<img src="[^"]+" alt="[^"]+" width="\d+" height="\d+" loading="lazy" decoding="async">'
        for featured, lead_src in ((True, "/sample/card.png"), (False, "/work/shots/desktop/test-shop-1.webp")):
            with self.subTest(featured=featured):
                if not featured:
                    os.remove(os.path.join(self.root, "_tools/data/featured.json"))
                page, _ = self.build()
                cards = re.findall(r'<li class="([^"]*)">(.*?)</li>', page, re.S)
                self.assertEqual(len(cards), 4 if featured else 3)
                self.assertEqual(cards[0][0], "work-card feature")
                imgs = [re.findall(r"<img [^>]*>", body) for _, body in cards]
                self.assertTrue(all(len(i) == 1 for i in imgs), imgs)
                self.assertRegex(imgs[0][0], "^%s$" % lead_img)
                self.assertIn('src="%s"' % lead_src, imgs[0][0])
                self.assertNotIn("loading=", imgs[0][0])
                for i in imgs[1:]:
                    self.assertRegex(i[0], "^%s$" % lazy_img)
                self.assertEqual(page.count('loading="lazy"'), len(cards) - 1)

    def test_feature_image_is_not_written_or_changed(self):
        folder = os.path.join(self.root, "sample")

        def snapshot():
            files = {}
            for n in os.listdir(folder):
                with open(os.path.join(folder, n), "rb") as f:
                    files[n] = f.read()
            return files

        before = snapshot()
        self.build()
        after = snapshot()
        self.assertEqual(before, after)

    def test_feature_is_not_in_samples_json(self):
        self.build()
        self.assertEqual([c["slug"] for c in json.loads(self.read("work/samples.json"))], ["bluebird-roofing"])

    def test_build_takes_the_feature_desktop_shot_from_its_page(self):
        asked = []
        real = bp.take_shots

        def fake(phone, desktop=(), pages=None):
            asked.append((list(phone), list(desktop), dict(pages or {})))
            return []
        bp.take_shots = fake
        try:
            self.assertEqual(self.run_main()[0], 0)
            put(self.root, "work/shots/desktop/granite-ridge-test.webp", "desktop")
            self.assertEqual(self.run_main()[0], 0)
            self.assertEqual(self.run_main("--shots")[0], 0)
            self.assertEqual(self.run_main("--no-shots")[0], 0)
        finally:
            bp.take_shots = real
        page = os.path.join(self.root, "sample", "index.html")
        self.assertEqual(asked[0], (["bluebird-roofing"], ["bluebird-roofing", "granite-ridge-test"],
                                    {"granite-ridge-test": page}))
        self.assertEqual(asked[1][1], ["bluebird-roofing"])                   # feature shot on disk: not retaken
        self.assertEqual(asked[2][1], ["bluebird-roofing", "granite-ridge-test"])
        self.assertEqual(len(asked), 3)                                       # --no-shots takes none

    def test_desktop_shot_page_defaults_to_the_design_page(self):
        self.assertEqual(bp.desktop_page("bluebird-roofing", {}),
                         os.path.join(self.root, "designs", "bluebird-roofing", "index.html"))
        self.assertEqual(bp.desktop_page("granite-ridge-test", {"granite-ridge-test": "/x/index.html"}), "/x/index.html")

    def test_check_notes_a_missing_feature_desktop_shot(self):
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("work/shots/desktop/granite-ridge-test.webp", out)
        self.assertIn("Feature card: Granite Ridge Masonry (/sample/)", out)

    def test_no_featured_file_leads_with_the_first_design(self):
        os.remove(os.path.join(self.root, "_tools/data/featured.json"))
        page, _ = self.build()
        self.assertIn('<li class="work-card feature"><div class="tag-row"><span class="tag tag-sample">Sample design'
                      '</span><span class="tag">Roofing</span>', page)
        self.assertNotIn('href="/sample/"', page)

    def test_feature_page_missing_is_a_note(self):
        os.remove(os.path.join(self.root, "sample/index.html"))
        page, out = self.build()
        self.assertIn("sample/index.html does not exist", out)
        self.assertNotIn('href="/sample/"', page)

    def test_feature_without_any_image_is_left_out_with_a_note(self):
        os.remove(os.path.join(self.root, "sample/card.png"))
        page, out = self.build()
        self.assertIn("no desktop shot and no sample/card.png", out)
        self.assertNotIn('href="/sample/"', page)
        self.assertNotIn("/sample/card.png", page)

    def test_bad_featured_json_stops_and_writes_nothing(self):
        cases = [dict(FEATURE, page="/samples/acme-roof-pros/"), dict(FEATURE, page="/designs/bluebird-roofing/"),
                 dict(FEATURE, page="https://example.com/"), dict(FEATURE, page="/../outside/"),
                 dict(FEATURE, page="sample/"), dict(FEATURE, page="/web-design/"),
                 dict(FEATURE, shot="bluebird-roofing"), dict(FEATURE, shot="acme-roof-pros"),
                 dict(FEATURE, shot="Bad Slug"), dict(FEATURE, image="/../card.png"),
                 dict(FEATURE, image="/sample/notes.txt"), dict(FEATURE, image="/samples/acme-roof-pros/a.png"),
                 {k: v for k, v in FEATURE.items() if k != "name"}, dict(FEATURE, name="  "),
                 dict(FEATURE, real="acme-roof-pros"), dict(FEATURE, line=3), [FEATURE]]
        for data in cases:
            with self.subTest(data=data):
                self.feature(data)
                code, out = self.run_main("--no-shots")
                self.assertEqual(code, 2, out)
                self.assertIn("featured.json", out)
                self.assertFalse(os.path.exists(os.path.join(self.root, "work")))
                self.assertFalse(os.path.exists(os.path.join(self.root, "sitemap.xml")))

    def test_feature_with_a_private_name_stops_the_build(self):
        self.feature(dict(FEATURE, line="Built by Acme Roof Pros."))
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 1, out)
        self.assertIn("acme roof pros", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))

    def test_feature_text_is_escaped(self):
        self.feature(dict(FEATURE, name="Granite & <b>Ridge</b>", line='A "stone" site.'))
        page, _ = self.build()
        self.assertIn("<h2>Granite &amp; &lt;b&gt;Ridge&lt;/b&gt;</h2>", page)
        self.assertIn('<p class="card-line">A &quot;stone&quot; site.</p>', page)

    def test_image_size_reads_png_and_webp(self):
        put_bytes(self.root, "a.png", png_head(640, 480))
        self.assertEqual(bp.image_size(os.path.join(self.root, "a.png")), (640, 480))
        vp8 = b"RIFF" + b"\x00" * 4 + b"WEBPVP8 " + b"\x00" * 4 + b"\x00" * 3 + b"\x9d\x01\x2a" + \
            (1000).to_bytes(2, "little") + (800).to_bytes(2, "little")
        put_bytes(self.root, "b.webp", vp8)
        self.assertEqual(bp.image_size(os.path.join(self.root, "b.webp")), (1000, 800))
        vp8x = b"RIFF" + b"\x00" * 4 + b"WEBPVP8X" + b"\x00" * 8 + (1199).to_bytes(3, "little") + (749).to_bytes(3, "little")
        put_bytes(self.root, "c.webp", vp8x)
        self.assertEqual(bp.image_size(os.path.join(self.root, "c.webp")), (1200, 750))
        put_bytes(self.root, "d.webp", b"not an image")
        self.assertIsNone(bp.image_size(os.path.join(self.root, "d.webp")))


def webp_head(w, h):
    """The first bytes of a WebP file of w x h: enough for the size reader."""
    return (b"RIFF" + b"\x00" * 4 + b"WEBPVP8X" + b"\x00" * 8 + (w - 1).to_bytes(3, "little")
            + (h - 1).to_bytes(3, "little"))


SIZES = 'sizes="(max-width: 599px) 93vw, 801px"'
ROOFER_ALT = 'alt="Desktop view of a sample design for a roofer in Testville"'
MASON_ALT = 'alt="Desktop view of a sample design for a stone mason in Testville"'


class SmallShots(SiteBase):
    """The 800 px copy of a card picture (work/shots/desktop/<slug>-800.webp): the card offers it to small
    screens with srcset and sizes when it is on disk, and the tag is the old one when it is not."""

    def setUp(self):
        super().setUp()
        self.town(True)
        put(self.root, "sample/index.html", FEATURE_PAGE)
        put_bytes(self.root, "sample/card.png", png_head(1000, 800))
        put(self.root, "_tools/data/featured.json", json.dumps(FEATURE))

    def shot(self, name, w, h):
        put_bytes(self.root, "work/shots/desktop/%s.webp" % name, webp_head(w, h))

    def imgs(self):
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        return re.findall(r"<img [^>]*>", self.read("work/index.html"))

    def test_card_with_an_800_copy_gets_srcset_and_sizes_after_height(self):
        self.shot("bluebird-roofing", 1200, 750)
        self.shot("bluebird-roofing-800", 800, 500)
        self.assertEqual(self.imgs()[1],
                         '<img src="/work/shots/desktop/bluebird-roofing.webp" ' + ROOFER_ALT +
                         ' width="1200" height="750" srcset="/work/shots/desktop/bluebird-roofing-800.webp 800w, '
                         '/work/shots/desktop/bluebird-roofing.webp 1200w" ' + SIZES +
                         ' loading="lazy" decoding="async">')

    def test_lead_card_with_an_800_copy_gets_srcset_and_stays_not_lazy(self):
        os.remove(os.path.join(self.root, "_tools/data/featured.json"))
        self.shot("bluebird-roofing", 1200, 750)
        self.shot("bluebird-roofing-800", 800, 500)
        self.assertEqual(self.imgs(),
                         ['<img src="/work/shots/desktop/bluebird-roofing.webp" ' + ROOFER_ALT +
                          ' width="1200" height="750" srcset="/work/shots/desktop/bluebird-roofing-800.webp 800w, '
                          '/work/shots/desktop/bluebird-roofing.webp 1200w" ' + SIZES + ' decoding="async">'])

    def test_card_without_an_800_copy_keeps_the_old_tag(self):
        self.shot("bluebird-roofing", 1200, 750)
        self.shot("granite-ridge-test", 1920, 1200)
        self.assertEqual(self.imgs(),
                         ['<img src="/work/shots/desktop/granite-ridge-test.webp" ' + MASON_ALT +
                          ' width="1200" height="750" decoding="async">',
                          '<img src="/work/shots/desktop/bluebird-roofing.webp" ' + ROOFER_ALT +
                          ' width="1200" height="750" loading="lazy" decoding="async">'])

    def test_a_1920_wide_shot_says_1920w_and_keeps_its_width_and_height(self):
        # the feature shot is kept at 1920 x 1200 on purpose; the tag still says 1200 x 750 (same shape)
        self.shot("granite-ridge-test", 1920, 1200)
        self.shot("granite-ridge-test-800", 800, 500)
        self.shot("bluebird-roofing", 1200, 750)
        imgs = self.imgs()
        self.assertEqual(imgs[0],
                         '<img src="/work/shots/desktop/granite-ridge-test.webp" ' + MASON_ALT +
                         ' width="1200" height="750" srcset="/work/shots/desktop/granite-ridge-test-800.webp 800w, '
                         '/work/shots/desktop/granite-ridge-test.webp 1920w" ' + SIZES + ' decoding="async">')
        # only the card that has a copy gets it
        self.assertNotIn("srcset", imgs[1])

    def test_only_a_real_800_copy_of_a_readable_wider_shot_is_offered(self):
        cases = {
            "the copy is not 800 px wide (another design's own shot)": ((1200, 750), (1200, 750)),
            "the copy is a different shape": ((1200, 750), (800, 800)),
            "the big shot is not wider than the copy": ((800, 500), (800, 500)),
        }
        for why, (big, small) in cases.items():
            with self.subTest(why=why):
                self.shot("bluebird-roofing", *big)
                self.shot("bluebird-roofing-800", *small)
                self.assertNotIn("srcset", "".join(self.imgs()))
        with self.subTest(why="the big shot cannot be read"):
            put(self.root, "work/shots/desktop/bluebird-roofing.webp", "desktop")
            self.shot("bluebird-roofing-800", 800, 500)
            self.assertNotIn("srcset", "".join(self.imgs()))
        with self.subTest(why="the copy cannot be read"):
            self.shot("bluebird-roofing", 1200, 750)
            put(self.root, "work/shots/desktop/bluebird-roofing-800.webp", "small")
            self.assertNotIn("srcset", "".join(self.imgs()))

    def test_feature_on_its_page_picture_never_gets_a_stray_800_copy(self):
        # no desktop shot yet, so the feature card shows /sample/card.png: a left over -800 file is another picture
        self.shot("granite-ridge-test-800", 800, 500)
        imgs = self.imgs()
        self.assertEqual(imgs[0], '<img src="/sample/card.png" ' + MASON_ALT +
                         ' width="1000" height="800" decoding="async">')

    def test_a_copy_one_pixel_off_in_height_still_counts(self):
        # 1200 x 751 scaled to 800 wide is 500.67 high: 500 or 501 are both the same picture
        self.shot("bluebird-roofing", 1200, 751)
        self.shot("bluebird-roofing-800", 800, 501)
        self.assertIn("bluebird-roofing-800.webp 800w", self.imgs()[1])

    # ---- the note when a desktop shot that has an 800 px copy is retaken

    def retake(self, new_bytes, *args):
        real = bp.take_shots

        def fake(phone, desktop=(), pages=None):
            for slug in desktop:
                if new_bytes is not None:
                    put_bytes(self.root, "work/shots/desktop/%s.webp" % slug, new_bytes)
            return []
        bp.take_shots = fake
        try:
            code, out = self.run_main(*args)
        finally:
            bp.take_shots = real
        self.assertEqual(code, 0, out)
        return out

    def test_retaking_a_shot_that_has_an_800_copy_says_to_remake_the_copy(self):
        self.shot("bluebird-roofing", 1200, 750)
        self.shot("bluebird-roofing-800", 800, 500)
        self.shot("granite-ridge-test", 1920, 1200)
        out = self.retake(webp_head(1200, 750) + b"new picture", "--shots")
        self.assertIn("Note: bluebird-roofing was retaken and its 800 px copy is from the old picture; "
                      "run python3 _tools/make_small_shots.py", out)
        # the feature shot was retaken too, but it has no copy, so no line names it
        self.assertEqual([ln for ln in out.splitlines() if "make_small_shots" in ln and "granite-ridge-test" in ln], [])
        self.assertEqual(out.count("make_small_shots"), 1)

    def test_no_remake_note_when_nothing_was_retaken(self):
        self.shot("bluebird-roofing", 1200, 750)
        self.shot("bluebird-roofing-800", 800, 500)
        self.shot("granite-ridge-test", 1920, 1200)
        self.assertNotIn("make_small_shots", self.retake(None, "--shots"))       # asked, but no new file came back
        self.assertNotIn("make_small_shots", self.retake(webp_head(1200, 750) + b"new", "--no-shots"))
        put(self.root, "work/shots/bluebird-roofing.webp", "phone")
        self.assertNotIn("make_small_shots", self.retake(webp_head(1200, 750) + b"new"))  # nothing missing

    def test_no_remake_note_for_a_first_shot_without_a_copy(self):
        out = self.retake(webp_head(1200, 750))
        self.assertNotIn("make_small_shots", out)


class Layout(SiteBase):
    """Mixed card sizes: which design cards run two columns wide so every grid row is full."""

    def test_wide_cards_fill_three_column_rows(self):
        cases = {0: set(), 1: set(), 2: {0}, 3: set(), 4: {0, 3}, 5: {3}, 6: set(), 7: {3, 6}, 8: {3}, 9: set(),
                 11: {3}}
        for n, want in cases.items():
            with self.subTest(n=n):
                wide = bp.wide_cards(n, 3)
                self.assertEqual(wide, want)
                if n >= 2:
                    self.assertEqual((n + len(wide)) % 3, 0)

    def test_wide_cards_fill_two_column_rows(self):
        for n, want in {0: set(), 1: {0}, 2: set(), 7: {6}, 8: set(), 9: {8}}.items():
            with self.subTest(n=n):
                self.assertEqual(bp.wide_cards(n, 2), want)

    def test_cards_carry_the_wide_classes(self):
        entries = [dict(ENTRY, real="real-shop-%d" % i, slug="test-shop-%d" % i, name="Test Shop %d" % i)
                   for i in range(1, 9)]
        for e in entries:
            put(self.root, "designs/%s/index.html" % e["slug"], DESIGN)
        shutil.rmtree(os.path.join(self.root, "designs", "bluebird-roofing"))
        self.designs(entries)
        put(self.root, "sample/index.html", FEATURE_PAGE)
        put_bytes(self.root, "sample/card.png", png_head(1000, 800))
        put(self.root, "_tools/data/featured.json", json.dumps(FEATURE))
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        classes = re.findall(r'<li class="([^"]*)">', self.read("work/index.html"))
        self.assertEqual(classes, ["work-card feature"] + ["work-card"] * 3 + ["work-card wide-3"] + ["work-card"] * 4)
        # one design less: odd count, so the last card runs wide in two columns too
        self.designs(entries[:7])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        classes = re.findall(r'<li class="([^"]*)">', self.read("work/index.html"))
        self.assertEqual(classes, ["work-card feature"] + ["work-card"] * 3 + ["work-card wide-3"] + ["work-card"] * 2
                         + ["work-card wide-3 wide-2"])


def visible(markup):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def faq_pairs(markup):
    return [(visible(q), visible(a)) for q, a in
            re.findall(r'<details class="faq-item"><summary>(.*?)</summary><p>(.*?)</p></details>', markup, re.S)]


class Tracked(unittest.TestCase):
    """Checks on the real site folder's tracked files. Read only, and no values are printed."""

    def test_tracked_designs_json_has_no_private_keys(self):
        with open(os.path.join(REAL_ROOT, "_tools", "data", "designs.json"), encoding="utf-8") as f:
            items = json.load(f)
        self.assertIsInstance(items, list)
        bad = [i + 1 for i, it in enumerate(items) if set(it) & set(bp.PRIVATE_DESIGN_KEYS)]
        self.assertEqual(bad, [], "designs.json entries with real or block (move them to designs.private.json)")

    def test_gitignore_lists_private_file(self):
        with open(os.path.join(REAL_ROOT, ".gitignore"), encoding="utf-8") as f:
            lines = [ln.strip() for ln in f]
        self.assertIn("_tools/data/designs.private.json", lines)


    def work_template(self):
        with open(os.path.join(REAL_ROOT, "_tools", "templates", "work.html"), encoding="utf-8") as f:
            return f.read()

    def test_work_faq_is_copied_word_for_word_from_the_faq_page(self):
        tpl = self.work_template()
        with open(os.path.join(REAL_ROOT, "faq", "index.html"), encoding="utf-8") as f:
            faq_page = dict(faq_pairs(f.read()))
        m = re.search(r'<section class="section(?: grid-bg)?" id="faq" aria-labelledby="faq-title">(.*?)</section>', tpl, re.S)
        self.assertIsNotNone(m, "no FAQ section on /work/")
        pairs = faq_pairs(m.group(1))
        self.assertIn(len(pairs), (3, 4))
        for q, a in pairs:
            self.assertIn(q, faq_page)
            self.assertEqual(a, faq_page[q])
        self.assertIn('<div class="faq center">', m.group(1))
        self.assertIn('<a class="link-arrow" href="/faq/">', m.group(1))
        self.assertNotIn('href="/work/"', m.group(1))                    # no link back to the same page
        self.assertNotRegex(visible(m.group(1)), "[-‐-―−]")

    def test_work_faq_sits_after_the_cards_and_before_the_closing_card(self):
        tpl = self.work_template()
        self.assertEqual(tpl.count("{{CARDS}}"), 1)
        self.assertLess(tpl.index("{{CARDS}}"), tpl.index('id="faq"'))
        self.assertLess(tpl.index('id="faq"'), tpl.index('class="section work-close"'))


if __name__ == "__main__":
    unittest.main()
