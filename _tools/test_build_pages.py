"""Tests for build_pages.py. Every test builds a small made up site in a temp folder; the real site is never
written. Only the Tracked tests read it (the tracked designs.json and .gitignore), and they print no values.
Run from the site folder:  python3 -m unittest discover -s _tools -p "test_*.py"
"""
import contextlib
import io
import json
import os
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


class Site(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gcd-test-")
        bp.set_root(self.root)
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
        self.designs([dict(ENTRY, trade="Lawn maintenance")])
        put(self.root, "designs/bluebird-roofing/index.html", with_ld('{"@type":"HomeAndConstructionBusiness"}'))
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn('alt="Phone view of a sample design for a lawn care business in Testville"', page)
        self.assertNotIn("home repair business", page)
        self.assertNotIn("a lawn maintenance in", page)

    def test_alt_text_ignores_plain_page_types(self):
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
        self.designs([dict(ENTRY, trade="Sandwiches")])
        code, out = self.run_main("--no-shots")
        self.assertEqual(code, 0, out)
        page = self.read("work/index.html")
        self.assertIn('alt="Phone view of a sample design for a sandwich shop in Testville"', page)
        self.assertNotIn("sandwiches business", page)

    def test_sitemap_only(self):
        code, _ = self.run_main("--sitemap")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, "work")))
        sitemap = self.read("sitemap.xml")
        self.assertNotIn("/designs/", sitemap)
        self.assertIn("<loc>https://granitecitydigital.me/faq/</loc>", sitemap)
        # the sitemap it writes passes its own check
        self.assertEqual(self.run_main("--check")[0], 0)


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


if __name__ == "__main__":
    unittest.main()
