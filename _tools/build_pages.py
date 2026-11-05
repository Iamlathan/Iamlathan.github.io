#!/usr/bin/env python3
"""Build the /work/ gallery (Sample designs), its phone screenshots, the sitemap and robots.txt,
and check that no private name, slug or phone number is public.

Run from the site folder:
  python3 _tools/build_pages.py            build work/, take missing shots, write the sitemap
  python3 _tools/build_pages.py --shots    retake every screenshot, not only the missing ones
  python3 _tools/build_pages.py --no-shots skip screenshots
  python3 _tools/build_pages.py --sitemap  write only sitemap.xml (and robots.txt if there is none)
  python3 _tools/build_pages.py --check    report problems and write nothing

Python 3 standard library only. See _tools/README.md.
"""
import argparse
import base64
import datetime
import fcntl
import hashlib
import html
import json
import os
import posixpath
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
from xml.sax.saxutils import escape as xml_escape

BASE_URL = "https://granitecitydigital.me"
SITE_HOSTS = {"granitecitydigital.me", "www.granitecitydigital.me"}
OWN_PHONE = "7432220985"

# Public pages for the sitemap, in order. The designs/<slug>/ pages are noindex, so they are never listed;
# /work/ (indexed) links them.
SITEMAP_PAGES = ["/", "/work/", "/sample/", "/faq/", "/service-area/", "/free-check/", "/privacy/", "/terms/"]

# URL folders that must never be linked from a public page. The shared logo mark folder is allowed.
PRIVATE_PREFIXES = ("/samples", "/web-design")
ALLOWED_PREFIXES = ("/samples/mark",)
# The old mark folder. GitHub Pages skips folders that start with "_", so a link to it 404s on the live site.
OLD_MARK_RE = re.compile(r"(?<![A-Za-z0-9])_mark/")
# schema.org types a design page may carry. Anything else (LocalBusiness, Restaurant, Plumber and so on)
# would read as a real business listing.
DESIGN_SCHEMA_OK = {"WebPage", "WebSite", "BreadcrumbList", "ListItem", "ImageObject", "CreativeWork"}
ITEMTYPE_RE = re.compile(r"""\bitemtype\s*=\s*["']([^"']*)["']""", re.I)
# Folders that are not public pages: unlisted pages and tools ("_" and "." folders are skipped too).
NOT_PUBLIC_DIRS = {"samples", "web-design", "node_modules"}
TEXT_EXTS = {".html", ".htm", ".js", ".mjs", ".json", ".css", ".xml", ".txt", ".svg", ".md", ".webmanifest"}
# Photos on designs/ and sample/ must not come from a page in samples/ (same file or same stock photo ID).
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg", ".bmp", ".tif", ".tiff", ".heic"}
CREDITS_FILE = "photo-credits.txt"
# samples/ folders that are not pages: the shared logo mark may be copied anywhere
SHARED_SAMPLE_DIRS = {"mark"}
PEXELS_ID_RE = re.compile(r"pexels\.com/(?:[a-z]{2}-[a-z]{2}/)?photos?/(?:[^\s/?#]*-)?(\d+)(?![\w-])", re.I)
UNSPLASH_ID_RE = re.compile(r"(?<![\w.])unsplash\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:photos|fotos)/([\w-]+)", re.I)
UNSPLASH_ID_LEN = 11

SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
LD_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
DESIGN_KEYS = ("real", "slug", "name", "trade", "town", "state")
# Private fields. They live only in the gitignored designs.private.json,
# never in the tracked designs.json (the repo is public).
PRIVATE_DESIGN_KEYS = ("real", "block")
PRIVATE_FILE = "designs.private.json"

# Screenshot settings
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOT_W, SHOT_H, SHOT_SCALE = 390, 736, 2
SHOT_QUALITIES = (80, 72, 64, 56, 48)
SHOT_MAX_BYTES = 120 * 1024
SETTLE_SECONDS = 3.0          # after the load event; the logo mark needs at least 2.5
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
FETCH_FILTER = {"patterns": [{"urlPattern": "*"}]}
AUTO_ATTACH = {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True}

# schema.org types used by the designs, as plain nouns for the alt text
SCHEMA_NOUNS = {
    "Restaurant": "restaurant", "CafeOrCoffeeShop": "coffee shop", "BeautySalon": "beauty salon",
    "HairSalon": "hair salon", "AutoRepair": "auto repair shop", "AutoBodyShop": "auto body shop",
    "Plumber": "plumber", "Electrician": "electrician", "HousePainter": "house painter",
    "GeneralContractor": "general contractor", "AccountingService": "tax and accounting office",
    "RoofingContractor": "roofer", "HVACBusiness": "HVAC company", "LandscapingBusiness": "landscaper",
}
# schema types too broad to name the business; the trade words are used instead
VAGUE_SCHEMA_TYPES = {"", "LocalBusiness", "HomeAndConstructionBusiness", "ProfessionalService", "Organization"}
# alt text noun picked from the first item of the trade, checked in order, before the schema type.
# Each pattern is matched as the start of a word, ignoring case.
TRADE_NOUNS = [
    ("lawn", "lawn care business"), ("mowing", "lawn care business"),
    ("tree", "tree service"), ("stump", "tree service"),
    ("landscap", "landscaper"), ("hardscap", "landscaper"), ("outdoor living", "landscaper"),
    ("pressure wash", "pressure washing business"), ("power wash", "pressure washing business"),
    ("soft wash", "pressure washing business"),
    ("seamless gutter", "gutter business"), ("gutter", "gutter business"),
    ("roof", "roofer"),
    ("concrete", "concrete contractor"), ("grading", "grading contractor"),
    ("fenc", "fence company"), ("pest", "pest control company"),
    ("clean", "cleaning business"), ("handyman", "handyman"),
    ("plumb", "plumber"), ("electric", "electrician"), ("hvac", "HVAC company"),
    # food: 'Sandwiches', 'Coffee and doughnuts', 'Southern breakfast and lunch' read badly as is
    ("coffee", "coffee shop"), ("doughnut", "doughnut shop"), ("donut", "doughnut shop"),
    ("sandwich", "sandwich shop"), ("burger", "burger shop"), ("pizza", "pizza shop"),
    ("breakfast", "breakfast restaurant"), ("diner", "diner"), ("bakery", "bakery"),
    ("barbecue", "barbecue restaurant"), ("bbq", "barbecue restaurant"),
    # shops and offices: body before repair, so 'Auto body' never reads as a repair shop
    ("auto body", "auto body shop"), ("body shop", "auto body shop"), ("collision", "auto body shop"),
    ("auto repair", "auto repair shop"), ("tire", "tire shop"),
    ("tax prep", "tax service"), ("tax service", "tax service"), ("bookkeep", "bookkeeping service"),
    ("skin", "skin care studio"), ("house paint", "house painter"),
]
# alt text noun for one design, keyed by the private slug (never printed); wins over everything else
SLUG_NOUNS = {}
# a trade ending in one of these names the work, not the business ("Auto repair", "Lawn maintenance")
SERVICE_WORDS = {"repair", "repairs", "care", "work", "service", "removal", "installation", "design",
                 "maintenance", "control", "cleanup"}
# words that do not make a name on their own ("The Lantern LLC" is too plain to search as "the lantern")
PLAIN_WORDS = {"the", "of", "and", "a", "an", "llc", "inc", "co"}
LEGAL_SUFFIX_RE = re.compile(r"[\s,]+(llc|l\.l\.c\.|inc\.?|co\.?)\s*$", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})(?!\d)")


def set_root(root):
    """Point every path at one site folder (the tests use a temp copy)."""
    global ROOT, TOOLS, TEMPLATES, DATA, SAMPLES, DESIGNS, WORK, SHOTS
    ROOT = os.path.abspath(root)
    TOOLS = os.path.join(ROOT, "_tools")
    TEMPLATES = os.path.join(TOOLS, "templates")
    DATA = os.path.join(TOOLS, "data")
    SAMPLES = os.path.join(ROOT, "samples")
    DESIGNS = os.path.join(ROOT, "designs")
    WORK = os.path.join(ROOT, "work")
    SHOTS = os.path.join(WORK, "shots")


set_root(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Raw(str):
    """Markup the script built itself (pieces already escaped); inserted as is."""


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_json(path):
    try:
        return json.loads(read(path))
    except json.JSONDecodeError as e:
        raise BuildError("%s is not valid JSON: %s" % (rel(path), e))


def rel(path):
    return os.path.relpath(path, ROOT)


def write_atomic(path, text_or_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = text_or_bytes.encode("utf-8") if isinstance(text_or_bytes, str) else text_or_bytes
    fd, tmp = tempfile.mkstemp(prefix=".build-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def esc(s):
    return html.escape(s, quote=True)


def json_inner(s):
    """A plain string made safe inside a JSON string inside a script tag."""
    return json.dumps(s, ensure_ascii=False)[1:-1].replace("<", "\\u003c")


def render(template, values, name):
    """Fill {{TOKENS}}. Plain strings are HTML escaped, or JSON escaped inside ld+json blocks."""
    wanted = set(TOKEN_RE.findall(template))
    unknown = sorted(wanted - set(values))
    if unknown:
        raise BuildError("template %s uses tokens the script does not fill: %s" % (name, ", ".join(unknown)))

    def sub_for(in_json):
        def sub(m):
            v = values[m.group(1)]
            if isinstance(v, Raw):
                return str(v)
            return json_inner(v) if in_json else esc(v)
        return sub

    out, pos = [], 0
    for m in LD_RE.finditer(template):
        out.append(TOKEN_RE.sub(sub_for(False), template[pos:m.start()]))
        out.append(m.group(1) + TOKEN_RE.sub(sub_for(True), m.group(2)) + m.group(3))
        pos = m.end()
    out.append(TOKEN_RE.sub(sub_for(False), template[pos:]))
    return "".join(out)


def page_file(url_path):
    """'/' -> index.html, '/faq/' -> faq/index.html"""
    return os.path.join(ROOT, url_path.strip("/"), "index.html") if url_path != "/" else os.path.join(ROOT, "index.html")


# ---------------------------------------------------------------- data

def title_name(page_html):
    """The business name in a page title 'Business | Trade in Town, NC', or ''."""
    m = re.search(r"<title>(.*?)</title>", page_html, re.S | re.I)
    if not m:
        return ""
    return html.unescape(m.group(1)).split(" | ", 1)[0].strip()


def real_samples():
    """Every page in samples/: {slug: business name from its title}."""
    out = {}
    if not os.path.isdir(SAMPLES):
        return out
    for slug in sorted(os.listdir(SAMPLES)):
        page = os.path.join(SAMPLES, slug, "index.html")
        if slug.startswith(("_", ".")) or not os.path.isfile(page):
            continue
        out[slug] = title_name(read(page))
    return out


def load_private(public_items):
    """Read the gitignored _tools/data/designs.private.json ({public slug: {"real": ..., "block": [...]}})
    and merge it into the public entries by slug. Returns new merged dicts, in the public order."""
    if not public_items:
        return []
    path = os.path.join(DATA, PRIVATE_FILE)
    if not os.path.isfile(path):
        raise BuildError("_tools/data/%s is missing, so nothing was built or checked. It holds the private slug and "
                         "block words for each design and is kept out of git on purpose. Put it back (from the "
                         "main working copy or a backup), then run again." % PRIVATE_FILE)
    private = load_json(path)
    if not isinstance(private, dict):
        raise BuildError("_tools/data/%s must be one JSON object keyed by the public slug" % PRIVATE_FILE)
    public_slugs = [it["slug"] for it in public_items]
    extra = sorted(set(private) - set(public_slugs))
    if extra:
        raise BuildError("%s has entries with no designs.json entry: %s" % (PRIVATE_FILE, ", ".join(extra)))
    merged = []
    for it in public_items:
        p = private.get(it["slug"])
        if p is None:
            raise BuildError("designs.json entry %s has no entry in %s" % (it["slug"], PRIVATE_FILE))
        if not isinstance(p, dict) or set(p) - set(PRIVATE_DESIGN_KEYS):
            raise BuildError("%s entry %s must be an object with only %s"
                             % (PRIVATE_FILE, it["slug"], " and ".join(PRIVATE_DESIGN_KEYS)))
        merged.append(dict(it, **p))
    return merged


def load_designs(samples):
    """Read _tools/data/designs.json (public facts only), merge in designs.private.json, and check the shape.
    Returns the list of merged entries."""
    path = os.path.join(DATA, "designs.json")
    if not os.path.isfile(path):
        raise BuildError("_tools/data/designs.json is missing (an empty list [] is fine)")
    public_items = load_json(path)
    if not isinstance(public_items, list):
        raise BuildError("_tools/data/designs.json must be one JSON list")
    for i, it in enumerate(public_items):
        if not isinstance(it, dict):
            raise BuildError("designs.json entry %d is not an object" % (i + 1))
        if not isinstance(it.get("slug"), str) or not it["slug"].strip():
            raise BuildError("designs.json entry %d has no slug" % (i + 1))
        private_here = [k for k in PRIVATE_DESIGN_KEYS if k in it]
        if private_here:
            raise BuildError("designs.json entry %d (%s) has %s. Those fields are private: move them to "
                             "_tools/data/%s, since designs.json is in the public repo"
                             % (i + 1, it["slug"], " and ".join(private_here), PRIVATE_FILE))
    items = load_private(public_items)
    seen_slug, seen_real = set(), set()
    for i, it in enumerate(items):
        where = "designs.json entry %d" % (i + 1)
        if not isinstance(it, dict):
            raise BuildError("%s is not an object" % where)
        for k in DESIGN_KEYS:
            if not isinstance(it.get(k), str) or not it[k].strip():
                raise BuildError("%s has no %s" % (where, k))
        for k in ("slug", "real"):
            if not SLUG_RE.fullmatch(it[k]):
                raise BuildError("%s: %s %r is not a lowercase slug" % (where, k, it[k]))
        block = it.get("block", [])
        if not isinstance(block, list) or not all(isinstance(b, str) and b.strip() for b in block):
            raise BuildError("%s: block must be a list of words or names" % where)
        if it["slug"] in seen_slug or it["real"] in seen_real:
            raise BuildError("%s repeats a slug or a private slug" % where)
        if it["slug"] == it["real"] or it["slug"] in samples or it["slug"] in ("mark", "_mark"):
            raise BuildError("%s: the public slug must not be a samples/ folder name" % where)
        seen_slug.add(it["slug"])
        seen_real.add(it["real"])
    return items


def template(name):
    return read(os.path.join(TEMPLATES, name))


# ---------------------------------------------------------------- designs and /work/

def schema_type(page_html):
    for t in re.findall(r'"@type"\s*:\s*"([^"]+)"', page_html):
        if t not in ("PostalAddress", "GeoCoordinates", "OpeningHoursSpecification", "Offer", "ListItem") \
                and t not in DESIGN_SCHEMA_OK:
            return t
    return ""


def schema_noun(t):
    if t in SCHEMA_NOUNS:
        return SCHEMA_NOUNS[t]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t).lower() if t else "local business"


def looks_like_service_list(trade):
    """'Coffee and doughnuts', 'House painting', 'Burgers on Main Street' read badly after 'a'."""
    head = trade.split(" on ")[0]
    if " and " in head or "," in head:
        return True
    last = head.split()[-1].lower() if head.split() else ""
    return (last.endswith("ing") or last in SERVICE_WORDS
            or (last.endswith("s") and not last.endswith("ss")))


def first_item(trade):
    """'Landscaping, hardscaping and outdoor living' -> 'Landscaping'; 'Diner on Main Street' -> 'Diner'."""
    head = trade.split(" on ")[0]
    return re.split(r",| and ", head)[0].strip()


def alt_noun(real, trade, page_type):
    """The business noun for the alt text: 'a ___ in Town'. Reads as a kind of business, never a service."""
    if real in SLUG_NOUNS:
        return SLUG_NOUNS[real]
    item = first_item(trade)
    for pattern, noun in TRADE_NOUNS:
        if re.search(r"\b" + re.escape(pattern), item, re.I):
            return noun
    if not looks_like_service_list(trade):
        return lower_first(item)
    if page_type not in VAGUE_SCHEMA_TYPES:
        return schema_noun(page_type)
    # a service with no clear schema type: 'Pressure washing' -> 'pressure washing business'
    words = lower_first(item)
    if not words:
        return "local business"
    if words.split()[-1].lower() in ("business", "company", "service", "shop", "studio", "office"):
        return words
    return words + " business"


def article(noun):
    first = noun.split()[0]
    if first.isupper() and len(first) > 1:            # acronyms like HVAC: "an H"
        return "an" if first[0] in "AEFHILMNORSX" else "a"
    return "an" if noun[0].lower() in "aeiou" else "a"


def lower_first(s):
    if len(s) > 1 and (s[1].isupper() or not s[1].isalpha()):   # keep "A/C", "HVAC"
        return s
    return s[:1].lower() + s[1:]


def collect_cards(designs):
    """One card per designs.json entry whose designs/<slug>/index.html exists, in designs.json order.
    A card holds only public facts."""
    cards, warnings = [], []
    for d in designs:
        slug = d["slug"]
        page = os.path.join(DESIGNS, slug, "index.html")
        if not os.path.isfile(page):
            warnings.append("designs/%s/index.html does not exist yet, so it has no card" % slug)
            continue
        trade, town, state = d["trade"].strip(), d["town"].strip(), d["state"].strip()
        kind = alt_noun(d["real"], trade, schema_type(read(page)))
        cards.append({
            "slug": slug,
            "name": d["name"].strip(),
            "trade": trade,
            "town": town,
            "state": state,
            "kind": kind,
            "alt": "Phone view of a sample design for %s %s in %s" % (article(kind), kind, town),
            "shot": "/work/shots/%s.webp" % slug,
            "preview": "/designs/%s/" % slug,
        })
    return cards, warnings


PUBLIC_CARD_KEYS = ("slug", "name", "trade", "town", "state", "alt", "shot", "preview")


def samples_json(cards):
    return json.dumps([{k: c[k] for k in PUBLIC_CARD_KEYS} for c in cards], indent=2, ensure_ascii=False) + "\n"


def shot_url(slug):
    """The shot file the page should point at: webp, or png when only a png exists."""
    if not os.path.isfile(os.path.join(SHOTS, slug + ".webp")) and os.path.isfile(os.path.join(SHOTS, slug + ".png")):
        return "/work/shots/%s.png" % slug
    return "/work/shots/%s.webp" % slug


def card_html(c):
    label = "Preview the sample design for %s, %s %s in %s" % (c["name"], article(c["kind"]), c["kind"], c["town"])
    return ('<li class="work-card"><img src="%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">'
            '<h2>%s</h2><p>%s in %s, %s</p><a class="link" href="%s" target="_blank" rel="noopener" aria-label="%s">Preview</a></li>') % (
        esc(c["shot"]), esc(c["alt"]), SHOT_W, SHOT_H, esc(c["name"]), esc(c["trade"]), esc(c["town"]), esc(c["state"]),
        esc(c["preview"]), esc(label))


def work_template():
    for name in ("work.html",):
        path = os.path.join(TEMPLATES, name)
        if os.path.isfile(path):
            return read(path), name
    raise BuildError("no _tools/templates/work.html")


def render_work(cards):
    tpl, name = work_template()
    return render(tpl, {"CARDS": Raw("\n".join(card_html(c) for c in cards))}, name), name


# ---------------------------------------------------------------- screenshots (headless Chrome over DevTools)

class Fail(Exception):
    pass


class Pipe:
    """DevTools over --remote-debugging-pipe: Chrome reads fd 3 and writes fd 4, messages end with a NUL byte."""

    def __init__(self, rfd, wfd):
        self.rfd, self.wfd = rfd, wfd
        self.buf = b""
        self.id = 0

    def send_json(self, obj):
        data = json.dumps(obj).encode() + b"\0"
        while data:
            n = os.write(self.wfd, data)
            data = data[n:]

    def recv_json(self, timeout=None):
        end = None if timeout is None else time.time() + timeout
        while b"\0" not in self.buf:
            wait = None if end is None else max(0, end - time.time())
            ready, _, _ = select.select([self.rfd], [], [], wait)
            if not ready:
                raise TimeoutError()
            chunk = os.read(self.rfd, 1 << 20)
            if not chunk:
                raise Fail("DevTools closed the connection")
            self.buf += chunk
        msg, self.buf = self.buf.split(b"\0", 1)
        return json.loads(msg.decode())

    def close(self):
        for fd in (self.rfd, self.wfd):
            try:
                os.close(fd)
            except OSError:
                pass


class Session:
    def __init__(self, ws, root):
        self.ws = ws
        self.sid = None
        self.events = []
        self.root = root          # real path of the site folder; only files under it may load
        self.attached = {}
        self.blocked = []

    def call(self, method, params=None, session=True):
        self.ws.id += 1
        mid = self.ws.id
        msg = {"id": mid, "method": method, "params": params or {}}
        if session and self.sid:
            msg["sessionId"] = self.sid
        self.ws.send_json(msg)
        while True:
            m = self.ws.recv_json(60)
            if m.get("id") == mid:
                if "error" in m:
                    raise Fail("%s failed: %s" % (method, m["error"].get("message", "")))
                return m.get("result", {})
            self.on_event(m)

    def on_event(self, m):
        meth = m.get("method")
        if meth == "Fetch.requestPaused":
            p = m["params"]
            url = p["request"]["url"]
            sid = m.get("sessionId")
            if self.allowed(url):
                self.send("Fetch.continueRequest", {"requestId": p["requestId"]}, sid)
            else:
                self.blocked.append(url)
                self.send("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"}, sid)
        elif meth == "Target.attachedToTarget":
            p = m["params"]
            sid = p["sessionId"]
            self.attached[p["targetInfo"]["targetId"]] = sid
            self.send("Fetch.enable", FETCH_FILTER, sid)
            self.send("Target.setAutoAttach", AUTO_ATTACH, sid)
            self.send("Runtime.runIfWaitingForDebugger", {}, sid)
        elif meth:
            self.events.append(meth)

    def send(self, method, params, sid):
        self.ws.id += 1
        self.ws.send_json({"id": self.ws.id, "method": method, "params": params, "sessionId": sid})

    def allowed(self, url):
        if url.startswith("data:"):
            return True
        u = urllib.parse.urlsplit(url)
        if u.scheme == "file":
            if u.netloc not in ("", "localhost"):
                return False
            path = os.path.realpath(urllib.parse.unquote(u.path))
            return path == self.root or path.startswith(self.root + os.sep)
        return u.scheme == "https" and (u.hostname or "").lower() in ALLOWED_HOSTS

    def wait_attached(self, target_id, seconds):
        end = time.time() + seconds
        while target_id not in self.attached:
            left = end - time.time()
            if left <= 0:
                raise Fail("page target did not attach")
            try:
                self.on_event(self.ws.recv_json(left))
            except TimeoutError:
                pass
        return self.attached[target_id]

    def wait_event(self, name, seconds):
        end = time.time() + seconds
        while name not in self.events:
            if time.time() > end:
                return False
            try:
                self.on_event(self.ws.recv_json(0.5))
            except TimeoutError:
                pass
        return True

    def pump(self, seconds):
        """Keep answering request events while the page settles."""
        end = time.time() + seconds
        while time.time() < end:
            try:
                self.on_event(self.ws.recv_json(max(0.05, end - time.time())))
            except TimeoutError:
                pass


WAIT_IMAGES = """
(async () => {
  document.querySelectorAll('img').forEach(i => { i.loading = 'eager'; });
  document.querySelectorAll('.rv').forEach(e => e.classList.add('in'));
  const imgs = Array.from(document.images);
  await Promise.all(imgs.map(i => i.complete ? Promise.resolve() :
    new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); setTimeout(r, 8000); })));
  if (document.fonts && document.fonts.ready) { await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 4000))]); }
  return imgs.length;
})()
"""


def capture(ses, page_path):
    """Phone capture of the top of one sample. Returns (bytes, format, quality)."""
    ses.events = []
    ses.call("Page.navigate", {"url": "file://" + urllib.parse.quote(os.path.realpath(page_path))})
    if not ses.wait_event("Page.loadEventFired", 30):
        raise Fail("page did not finish loading")
    loaded = time.time()
    ses.call("Runtime.evaluate", {"expression": WAIT_IMAGES, "awaitPromise": True, "returnByValue": True})
    ses.call("Runtime.evaluate", {"expression": "window.scrollTo(0,0)"})
    ses.pump(max(0.0, SETTLE_SECONDS - (time.time() - loaded)))
    clip = {"x": 0, "y": 0, "width": SHOT_W, "height": SHOT_H, "scale": 1}
    data = None
    for q in SHOT_QUALITIES:
        try:
            shot = ses.call("Page.captureScreenshot", {"format": "webp", "quality": q, "clip": clip})
        except Fail:
            break
        data = base64.b64decode(shot["data"])
        if not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            data = None
            break
        if len(data) <= SHOT_MAX_BYTES:
            return data, "webp", q
    if data is not None:
        return data, "webp", SHOT_QUALITIES[-1]
    shot = ses.call("Page.captureScreenshot", {"format": "png", "clip": clip})
    return base64.b64decode(shot["data"]), "png", None


def kill_group(proc):
    """Stop the Chrome this script started (its own process group), nothing else."""
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            break
        end = time.time() + wait
        while time.time() < end:
            if proc.poll() is not None:
                return
            time.sleep(0.1)
    proc.poll()


def take_shots(slugs):
    """Returns a list of report lines. Writes work/shots/<slug>.webp (or .png on fallback)."""
    if not slugs:
        return []
    if not os.access(CHROME, os.X_OK):
        return ["SHOTS BLOCKED: no Google Chrome at " + CHROME]
    os.makedirs(SHOTS, exist_ok=True)
    report = []
    profile = tempfile.mkdtemp(prefix="gcd-chrome-")
    proc = ws = None

    def on_alarm(signum, frame):
        raise Fail("screenshot timeout")

    signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(60 + 25 * len(slugs))
    try:
        c_in, p_out = os.pipe()
        p_in, c_out = os.pipe()
        c_in, c_out = fcntl.fcntl(c_in, fcntl.F_DUPFD, 10), fcntl.fcntl(c_out, fcntl.F_DUPFD, 10)

        def child_fds():
            os.dup2(c_in, 3)
            os.dup2(c_out, 4)

        try:
            proc = subprocess.Popen(
                [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                 "--no-default-browser-check", "--disable-extensions", "--remote-debugging-pipe",
                 "--user-data-dir=" + profile, "about:blank"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                preexec_fn=child_fds, close_fds=False, start_new_session=True)
        finally:
            os.close(c_in)
            os.close(c_out)
        ws = Pipe(p_in, p_out)
        ses = Session(ws, os.path.realpath(ROOT))
        ses.call("Target.setAutoAttach", AUTO_ATTACH, session=False)
        tid = ses.call("Target.createTarget", {"url": "about:blank"}, session=False)["targetId"]
        ses.sid = ses.wait_attached(tid, 30)
        ses.call("Page.enable")
        ses.call("Emulation.setDeviceMetricsOverride", {
            "width": SHOT_W, "height": SHOT_H, "deviceScaleFactor": SHOT_SCALE, "mobile": True,
            "screenWidth": SHOT_W, "screenHeight": SHOT_H})
        ses.call("Emulation.setTouchEmulationEnabled", {"enabled": True})
        for slug in slugs:
            ses.blocked = []
            try:
                data, fmt, q = capture(ses, os.path.join(DESIGNS, slug, "index.html"))
            except Fail as e:
                report.append("shot %s FAILED: %s" % (slug, e))
                continue
            path = os.path.join(SHOTS, "%s.%s" % (slug, fmt))
            write_atomic(path, data)
            line = "shot %s: %s, %d KB" % (rel(path), fmt if q is None else "%s q%d" % (fmt, q), len(data) // 1024)
            if fmt == "png":
                line += " (PNG FALLBACK: Chrome would not make webp)"
            elif len(data) > SHOT_MAX_BYTES:
                line += " (OVER 120 KB at the lowest quality tried)"
            if ses.blocked:
                line += "; blocked %d outside request(s): %s" % (len(ses.blocked), ", ".join(sorted(set(ses.blocked))[:3]))
            report.append(line)
    except (Fail, OSError, ValueError, KeyError, TimeoutError) as e:
        report.append("SHOTS STOPPED: %s" % e)
    finally:
        signal.alarm(0)
        if ws:
            ws.close()
        if proc:
            kill_group(proc)
        shutil.rmtree(profile, ignore_errors=True)
    return report



def remove_old_shots(real_slugs):
    """Remove work/shots files named after a private slug: git rm when tracked, else delete.
    Only those names are touched; every other file in work/shots stays."""
    removed = []
    if not os.path.isdir(SHOTS):
        return removed
    for name in sorted(os.listdir(SHOTS)):
        stem, ext = os.path.splitext(name)
        path = os.path.join(SHOTS, name)
        if stem not in real_slugs or ext.lower() not in (".webp", ".png") or not os.path.isfile(path):
            continue
        tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "--error-unmatch", "--", rel(path)],
                                 capture_output=True, text=True).returncode == 0
        if tracked:
            subprocess.run(["git", "-C", ROOT, "rm", "-q", "--", rel(path)], check=True)
        else:
            os.remove(path)
        removed.append(rel(path) + (" (git rm)" if tracked else ""))
    return removed


# ---------------------------------------------------------------- sitemap, robots

def sitemap_paths():
    """Public pages that exist on disk, in sitemap order, and the ones left out because they are missing."""
    have = [p for p in SITEMAP_PAGES if os.path.isfile(page_file(p))]
    return have, [p for p in SITEMAP_PAGES if p not in have]


def sitemap_xml(paths, today):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in paths:
        lines.append("  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (xml_escape(BASE_URL + p), today))
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


ROBOTS = "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE_URL


def write_sitemap():
    have, missing = sitemap_paths()
    today = datetime.date.today().isoformat()
    write_atomic(os.path.join(ROOT, "sitemap.xml"), sitemap_xml(have, today))
    robots_note = "kept as is"
    if not os.path.exists(os.path.join(ROOT, "robots.txt")):
        write_atomic(os.path.join(ROOT, "robots.txt"), ROBOTS)
        robots_note = "written"
    print("Wrote sitemap.xml with %d URLs (lastmod %s); robots.txt %s" % (len(have), today, robots_note))
    for p in missing:
        print("  left out, no page on disk yet: %s" % p)


# ---------------------------------------------------------------- privacy: private names stay off public pages

def norm(s):
    """Lower case words only, apostrophes dropped and & read as 'and', padded with spaces for whole word search."""
    s = html.unescape(s).lower()
    s = re.sub(r"['‘’`´]", "", s).replace("&", " and ")
    return " %s " % " ".join(re.findall(r"[a-z0-9]+", s))


def strong(phrase):
    """True when a normalized phrase has at least two words that are not plain filler."""
    return len([w for w in phrase.split() if w not in PLAIN_WORDS]) >= 2


def private_terms(designs, samples):
    """What must never show up in public: private slugs, private business names (with and without LLC), extra
    names from each entry's "block" list, and the phone numbers on the samples/ pages."""
    slugs, phrases, phones = set(samples), {}, set()
    for d in designs:
        slugs.add(d["real"])
        for b in d.get("block", []):
            phrases[norm(b).strip()] = "blocked name from designs.json"
    for slug in sorted(slugs):
        name = samples.get(slug, "")
        for v in (name, LEGAL_SUFFIX_RE.sub("", name), slug.replace("-", " ")):
            p = norm(v).strip()
            if p and strong(p):
                phrases.setdefault(p, "private name of samples/%s" % slug)
        page = os.path.join(SAMPLES, slug, "index.html")
        if os.path.isfile(page):
            for a, b, c in PHONE_RE.findall(html.unescape(read(page))):
                if b != "555" and a + b + c != OWN_PHONE:
                    phones.add(a + b + c)
    return {"slugs": slugs, "phrases": phrases, "phones": phones}


def leaks_in_text(text, terms):
    """Labels for every private slug, name or phone number found in one text."""
    found = set()
    low = text.lower()
    for s in terms["slugs"]:
        if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(s), low):
            found.add("private slug %s" % s)
    stripped = re.sub(r"<[^>]+>", " ", text)
    hay = norm(text) + norm(stripped)
    for p, why in terms["phrases"].items():
        if " %s " % p in hay:
            found.add("%r (%s)" % (p, why))
    for a, b, c in PHONE_RE.findall(html.unescape(text)):
        if a + b + c in terms["phones"]:
            found.add("private phone number ending %s" % c)
    return found


def walk_files(top):
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if not name.startswith("."):
                yield os.path.join(dirpath, name)


def scan_private(terms, extra=()):
    """Scan file names and text in work/, designs/ and sitemap.xml, plus extra (label, text) pairs that are
    about to be written. Returns a list of 'where: what' lines."""
    hits = []
    files = []
    for top in (WORK, DESIGNS):
        if os.path.isdir(top):
            files.extend(walk_files(top))
    if os.path.isfile(os.path.join(ROOT, "sitemap.xml")):
        files.append(os.path.join(ROOT, "sitemap.xml"))
    for path in files:
        r = rel(path)
        found = {f for f in leaks_in_text(r.replace(os.sep, "/"), terms) if f.startswith("private slug")}
        if os.path.splitext(path)[1].lower() in TEXT_EXTS:
            try:
                found |= leaks_in_text(read(path), terms)
            except UnicodeDecodeError:
                pass
        hits.extend("%s: %s" % (r, f) for f in sorted(found))
    for label, text in extra:
        hits.extend("%s: %s" % (label, f) for f in sorted(leaks_in_text(text, terms)))
    return hits


# ---------------------------------------------------------------- public links and noindex

ATTR_RE = re.compile(r"""\b(href|src|srcset|action|poster|content|data-[\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
LITERAL_RE = re.compile(r"""["'`(=]\s*(/(?:samples|web-design)(?=[/"'`)\s?#])[^\s"'`<>)]*)""")
ABS_RE = re.compile(r"""(?:https?:)?//(?:www\.)?granitecitydigital\.me(/[^\s"'`<>)]*)""", re.I)


def is_private_path(path):
    p = posixpath.normpath(urllib.parse.unquote(path.split("?")[0].split("#")[0]) or "/")
    if any(p == a or p.startswith(a + "/") for a in ALLOWED_PREFIXES):
        return False
    return any(p == x or p.startswith(x + "/") for x in PRIVATE_PREFIXES)


def page_url(path):
    r = rel(path).replace(os.sep, "/")
    if r == "index.html":
        return "/"
    if r.endswith("/index.html"):
        return "/" + r[:-len("index.html")]
    return "/" + r


def public_files():
    """Every text file GitHub Pages would serve, minus the unlisted pages and tool folders."""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        top = os.path.relpath(dirpath, ROOT) == "."
        dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "_")) and not (top and d in NOT_PUBLIC_DIRS))
        for name in sorted(filenames):
            if not name.startswith((".", "_")) and os.path.splitext(name)[1].lower() in TEXT_EXTS:
                yield os.path.join(dirpath, name)


def private_links_in(path, text):
    refs = set()
    base = BASE_URL + page_url(path)
    if os.path.splitext(path)[1].lower() in (".html", ".htm", ".svg"):
        for m in ATTR_RE.finditer(text):
            value = html.unescape(m.group(2) if m.group(2) is not None else m.group(3) or "").strip()
            values = [v.strip().split(" ")[0] for v in value.split(",")] if m.group(1).lower() == "srcset" else [value]
            for v in values:
                if not v or v.startswith(("mailto:", "tel:", "sms:", "data:", "javascript:", "#")):
                    continue
                u = urllib.parse.urlsplit(urllib.parse.urljoin(base, v))
                if (u.hostname or "").lower() in SITE_HOSTS and is_private_path(u.path):
                    refs.add(v)
    for m in LITERAL_RE.finditer(text):
        if is_private_path(m.group(1)):
            refs.add(m.group(1))
    for m in ABS_RE.finditer(text):
        if is_private_path(m.group(1)):
            refs.add(m.group(0))
    return refs


def scan_links():
    hits = []
    for path in public_files():
        try:
            text = read(path)
        except UnicodeDecodeError:
            continue
        hits.extend("%s: %s" % (rel(path), r) for r in sorted(private_links_in(path, text)))
    return hits


def has_noindex(page_html):
    for tag in re.findall(r"<meta\b[^>]*>", page_html, re.I):
        attrs = {k.lower(): (v1 if v1 is not None else v2) for k, v1, v2 in
                 re.findall(r"""([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", tag)}
        if attrs.get("name", "").lower() in ("robots", "googlebot") and "noindex" in attrs.get("content", "").lower():
            return True
    return False


def scan_noindex():
    """Every html page inside samples/<slug>/ needs a noindex robots meta ("_" and "." folders are skipped)."""
    hits = []
    if not os.path.isdir(SAMPLES):
        return hits
    for slug in sorted(os.listdir(SAMPLES)):
        folder = os.path.join(SAMPLES, slug)
        if slug.startswith(("_", ".")) or not os.path.isdir(folder):
            continue
        for path in walk_files(folder):
            if path.lower().endswith((".html", ".htm")) and not has_noindex(read(path)):
                hits.append(rel(path))
    return hits


def design_pages():
    """Every designs/<slug>/index.html on disk, listed in designs.json or not ("_" and "." folders are skipped)."""
    if not os.path.isdir(DESIGNS):
        return []
    out = []
    for slug in sorted(os.listdir(DESIGNS)):
        page = os.path.join(DESIGNS, slug, "index.html")
        if not slug.startswith(("_", ".")) and os.path.isfile(page):
            out.append(page)
    return out


def scan_design_noindex():
    """Every designs/<slug>/index.html needs a noindex robots meta."""
    return [rel(p) for p in design_pages() if not has_noindex(read(p))]


def ld_types(node):
    """Every @type value anywhere in one parsed JSON-LD value."""
    found = []
    if isinstance(node, dict):
        t = node.get("@type")
        for v in (t if isinstance(t, list) else [t]):
            if isinstance(v, str) and v.strip():
                found.append(v.strip())
        for v in node.values():
            found.extend(ld_types(v))
    elif isinstance(node, list):
        for v in node:
            found.extend(ld_types(v))
    return found


def schema_short(t):
    """'https://schema.org/Plumber' or 'schema:Plumber' -> 'Plumber'."""
    return re.split(r"[/:#]", t.strip())[-1]


def scan_design_schema():
    """Business structured data on design pages: any JSON-LD or microdata itemtype that is not a plain
    page type (DESIGN_SCHEMA_OK). A JSON-LD block that does not parse is a hit too, since it cannot be checked."""
    hits = []
    for page in design_pages():
        text = read(page)
        bad = set()
        for m in re.finditer(r"""<script\b[^>]*\btype\s*=\s*["']?application/ld\+json["']?[^>]*>(.*?)</script\s*>""",
                             text, re.I | re.S):
            try:
                types = ld_types(json.loads(m.group(1)))
            except ValueError:
                bad.add("JSON-LD that does not parse")
                continue
            bad.update("JSON-LD @type %s" % t for t in types if schema_short(t) not in DESIGN_SCHEMA_OK)
        for m in ITEMTYPE_RE.finditer(text):
            bad.update("microdata itemtype %s" % schema_short(u) for u in m.group(1).split()
                       if schema_short(u) not in DESIGN_SCHEMA_OK)
        hits.extend("%s: %s" % (rel(page), b) for b in sorted(bad))
    return hits


def scan_old_mark():
    """Links to the old _mark/ folder in any text file under samples/ or designs/, and the folder itself."""
    hits = []
    if os.path.exists(os.path.join(SAMPLES, "_mark")):
        hits.append("samples/_mark/ (folder on disk; the mark lives in samples/mark/)")
    for top in (SAMPLES, DESIGNS):
        if not os.path.isdir(top):
            continue
        for path in walk_files(top):
            if os.path.splitext(path)[1].lower() not in TEXT_EXTS:
                continue
            try:
                text = read(path)
            except UnicodeDecodeError:
                continue
            lines = sorted({text.count("\n", 0, m.start()) + 1 for m in OLD_MARK_RE.finditer(text)})
            if lines:
                hits.append("%s: line %s" % (rel(path), ", ".join(str(n) for n in lines[:5])))
    return hits


# ---------------------------------------------------------------- photos reused from samples/

def photo_ids(text):
    """Every Pexels and Unsplash photo ID in one credits text, as 'Pexels photo 1234567' or
    'Unsplash photo AbCdEfGhIjK'. Unsplash IDs are the last 11 characters of the link and keep their case."""
    ids = {"Pexels photo %s" % m.group(1) for m in PEXELS_ID_RE.finditer(text)}
    for m in UNSPLASH_ID_RE.finditer(text):
        part = m.group(1)
        if len(part) >= UNSPLASH_ID_LEN and (len(part) == UNSPLASH_ID_LEN or part[-UNSPLASH_ID_LEN - 1] == "-"):
            ids.add("Unsplash photo %s" % part[-UNSPLASH_ID_LEN:])
    return ids


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def lead_sample_files():
    """Every file in the folders samples/<slug>/ (not "_" or "." folders, not the shared mark)."""
    if not os.path.isdir(SAMPLES):
        return []
    out = []
    for slug in sorted(os.listdir(SAMPLES)):
        folder = os.path.join(SAMPLES, slug)
        if slug.startswith(("_", ".")) or slug in SHARED_SAMPLE_DIRS or not os.path.isdir(folder):
            continue
        out.extend(walk_files(folder))
    return out


def made_up_files():
    """Every file on the made up pages: designs/<slug>/ (not "_" or "." folders) and sample/."""
    out = []
    if os.path.isdir(DESIGNS):
        for slug in sorted(os.listdir(DESIGNS)):
            folder = os.path.join(DESIGNS, slug)
            if not slug.startswith(("_", ".")) and os.path.isdir(folder):
                out.extend(walk_files(folder))
    sample = os.path.join(ROOT, "sample")
    if os.path.isdir(sample):
        out.extend(walk_files(sample))
    return out


def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def scan_reused_photos():
    """Images on designs/ and sample/ that are byte for byte (sha256) an image in samples/, and Pexels or
    Unsplash photo IDs in their photo-credits.txt that a samples/ photo-credits.txt also lists."""
    hits = []
    lead_hashes, lead_ids = {}, {}
    for path in lead_sample_files():
        if is_image(path):
            lead_hashes.setdefault(sha256_of(path), rel(path))
        elif os.path.basename(path) == CREDITS_FILE:
            try:
                for i in photo_ids(read(path)):
                    lead_ids.setdefault(i, rel(path))
            except UnicodeDecodeError:
                pass
    for path in made_up_files():
        if is_image(path):
            match = lead_hashes.get(sha256_of(path))
            if match:
                hits.append("%s: same bytes as %s" % (rel(path), match))
        elif os.path.basename(path) == CREDITS_FILE:
            try:
                ids = photo_ids(read(path))
            except UnicodeDecodeError:
                hits.append("%s: not UTF-8 text, so its photo IDs cannot be checked" % rel(path))
                continue
            hits.extend("%s: %s, also in %s" % (rel(path), i, lead_ids[i]) for i in sorted(ids) if i in lead_ids)
    return hits


# ---------------------------------------------------------------- check

def section(title, items, problem=True):
    print("\n%s: %s" % (title, "none" if not items else len(items)))
    for x in items[:40]:
        print("  " + x)
    if len(items) > 40:
        print("  ... and %d more" % (len(items) - 40))
    return len(items) if problem else 0


def run_check(designs, samples, cards, card_notes, work_html, json_text):
    print("CHECK (nothing written)")
    problems = 0
    print("\ndesigns.json: %d entries, %d with a page in designs/ (cards on /work/)" % (len(designs), len(cards)))
    for n in card_notes:
        print("  Note: " + n)
    mapped = {d["real"] for d in designs}
    section("Note: pages in samples/ with no designs.json entry yet (not on /work/)",
            sorted(s for s in samples if s not in mapped), problem=False)
    listed = {d["slug"] for d in designs}
    stray = sorted(s for s in (os.listdir(DESIGNS) if os.path.isdir(DESIGNS) else [])
                   if not s.startswith((".", "_")) and s not in listed)
    section("Note: folders in designs/ with no designs.json entry (not on /work/)", stray, problem=False)
    left = sorted(set(TOKEN_RE.findall(work_html)))
    problems += section("Leftover {{TOKENS}} in the /work/ page", left)
    problems += section("Pages in samples/ without a noindex robots meta", scan_noindex())
    problems += section("Pages in designs/ without a noindex robots meta", scan_design_noindex())
    problems += section("Business structured data on designs/ pages (LocalBusiness style JSON-LD or microdata)",
                        scan_design_schema())
    problems += section("Old _mark/ links or folder in samples/ or designs/ (use mark/)", scan_old_mark())
    problems += section("web-design/ folder still on disk", ["web-design/"] if os.path.exists(os.path.join(ROOT, "web-design")) else [])
    problems += section("Public files linking to /samples/ or /web-design/", scan_links())
    problems += section("Images or stock photo IDs on designs/ or sample/ reused from a page in samples/",
                        scan_reused_photos())
    terms = private_terms(designs, samples)
    problems += section("Private slugs, names or phone numbers in work/, designs/, sitemap.xml or the /work/ build",
                        scan_private(terms, [("(built) work/index.html", work_html), ("(built) work/samples.json", json_text)]))
    have, missing = sitemap_paths()
    section("Note: sitemap pages with no page on disk yet (left out until they exist)", missing, problem=False)
    on_disk = os.path.join(ROOT, "sitemap.xml")
    current = re.findall(r"<loc>([^<]*)</loc>", read(on_disk)) if os.path.isfile(on_disk) else []
    problems += section("sitemap.xml lists noindex designs/ pages (run --sitemap to rewrite it)",
                        [u for u in current if "/designs/" in u])
    if current != [BASE_URL + p for p in have]:
        print("\nNote: sitemap.xml differs from what the build would write (%d URLs now, %d after a build)" % (len(current), len(have)))
    print("\nRESULT: %s" % ("OK" if not problems else "%d problem(s)" % problems))
    return 1 if problems else 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Build /work/ (Sample designs), shots and the sitemap; check privacy.")
    ap.add_argument("--check", action="store_true", help="report problems and write nothing")
    ap.add_argument("--shots", action="store_true", help="retake every screenshot")
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots")
    ap.add_argument("--sitemap", action="store_true", help="write only sitemap.xml (and robots.txt if missing)")
    args = ap.parse_args(argv)
    if os.path.realpath(os.getcwd()) != os.path.realpath(ROOT):
        print("Note: run from the site folder; using %s" % ROOT)

    try:
        samples = real_samples()
        designs = load_designs(samples)
        if args.sitemap:
            write_sitemap()
            return 0
        cards, card_notes = collect_cards(designs)
        for c in cards:
            c["shot"] = shot_url(c["slug"])
        work_html, work_name = render_work(cards)
        json_text = samples_json(cards)
    except BuildError as e:
        print("ERROR: %s" % e)
        return 2

    if args.check:
        return run_check(designs, samples, cards, card_notes, work_html, json_text)

    for n in card_notes:
        print("Note: " + n)
    if not cards:
        print("STOPPED: no designs/<slug>/ pages listed in _tools/data/designs.json yet, so work/ was left as is.")
        return 1
    reused = scan_reused_photos()
    if reused:
        print("STOPPED, nothing written: images or stock photo IDs reused from a page in samples/")
        for h in reused:
            print("  " + h)
        return 1
    terms = private_terms(designs, samples)
    # Guard before anything is written or shot: the design pages and the new /work/ must hold no private names.
    pre = [h for h in scan_private(terms, [("(built) work/index.html", work_html), ("(built) work/samples.json", json_text)])
           if not h.startswith(("work/", "sitemap.xml"))]
    if pre:
        print("STOPPED, nothing written: private names, slugs or phone numbers found")
        for h in pre:
            print("  " + h)
        return 1

    if not args.no_shots:
        todo = [c["slug"] for c in cards if args.shots or not os.path.isfile(os.path.join(SHOTS, c["slug"] + ".webp"))]
        for line in take_shots(todo):
            print(line)
        for c in cards:
            c["shot"] = shot_url(c["slug"])
        work_html, work_name = render_work(cards)
        json_text = samples_json(cards)
    write_atomic(os.path.join(WORK, "index.html"), work_html)
    write_atomic(os.path.join(WORK, "samples.json"), json_text)
    print("Wrote work/index.html from %s with %d cards, and work/samples.json" % (work_name, len(cards)))
    for r in remove_old_shots(terms["slugs"]):
        print("Removed old shot " + r)
    missing_shots = [c["slug"] for c in cards if not os.path.isfile(os.path.join(ROOT, c["shot"].lstrip("/")))]
    if missing_shots:
        print("Note: no shot yet for %s" % ", ".join(missing_shots))
    write_sitemap()

    post = scan_private(terms) + scan_links()
    if post:
        print("\nAFTER BUILD, still found (fix before publishing):")
        for h in post:
            print("  " + h)
        return 1
    print("\nAfter build: no private names, slugs or phone numbers in work/, designs/ or sitemap.xml; no public links to /samples/ or /web-design/;"
          "\nno images or stock photo IDs on designs/ or sample/ reused from samples/."
          "\nRun --check too: it also covers noindex and structured data on designs/ and old _mark/ links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
