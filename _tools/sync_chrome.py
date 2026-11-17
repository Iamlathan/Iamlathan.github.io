#!/usr/bin/env python3
"""Stamp the shared header, footer and floating bar from one source page into other main site pages.

usage (from the site folder):
  python3 _tools/sync_chrome.py --check --all     report what would change, write nothing
  python3 _tools/sync_chrome.py --all             stamp every main page plus the /work/ template
  python3 _tools/sync_chrome.py [--source index.html] [--check] PAGE [PAGE ...]
PAGE is a path inside the site folder (relative to it, or absolute), for example services/local-seo/index.html.
The site folder is the folder above _tools/. --all means the main pages in MAIN_PAGES below.
Then check the result with:  python3 _tools/blocks_check.py

What it does, per page:
- Copies the three blocks from the source page: <header class="site-header">, <footer class="site-footer">
  and <div class="fbar">. The current page marks of the source (aria-current="page", the is-current class) are removed first.
- Sets the marks for the target page: aria-current="page" on every top bar, phone menu, Services panel and footer link
  that points to this page (never on the brand link or the yellow Contact us buttons), and the is-current class on the
  Services buttons (top bar and phone menu) when the page is one of the Services panel links.
  /free-check/ counts as /services/free-website-check/. The work template counts as /work/.
- Keeps the slim header of /get-started/ (logo and Call only) and points its floating bar button at #start.
- A page that lacks one of the blocks is reported and that block is left alone (nothing is inserted).
- Refuses sample/, designs/ and samples/ and anything outside the site folder.
- --check writes nothing and exits 1 if any page would change.
Prints what it changed. Running it twice changes nothing the second time.
"""
import os, re, sys

# the site folder: the parent of the _tools/ folder this file sits in
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# every main page with the shared blocks, plus the /work/ template (build_pages.py makes /work/ from it)
MAIN_PAGES = ["index.html", "about/index.html", "client-portal/index.html", "contact/index.html", "faq/index.html",
              "free-check/index.html", "get-started/index.html", "privacy/index.html", "terms/index.html",
              "service-area/index.html", "work/index.html", "services/care-plan/index.html",
              "services/free-website-check/index.html", "services/website-design/index.html",
              "services/website-rebuild/index.html", "404.html",
              "services/google-business-profile/index.html", "services/local-seo/index.html",
              "services/logo-and-brand-kit/index.html", "websites-for/home-services/index.html",
              "websites-for/auto-shops/index.html", "websites-for/food-and-coffee/index.html",
              "websites-for/beauty-and-wellness/index.html", "_tools/templates/work.html"]
REFUSE = ("sample", "designs", "samples")
ALIAS = {"/free-check/": "/services/free-website-check/"}

BLOCKS = {
    "header": re.compile(r'<header class="site-header".*?</header>', re.S),
    "footer": re.compile(r'<footer class="site-footer">.*?</footer>', re.S),
    "fbar": re.compile(r'<div class="fbar".*?\n</div>', re.S),
}


def strip_marks(s):
    s = re.sub(r'\s+aria-current="page"', '', s)
    return s.replace(' is-current', '')


def url_for(rel):
    if rel == "_tools/templates/work.html":
        return "/work/"
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[:-len("index.html")]
    return None  # 404.html and other loose files: no current page


def mark_header(h, url):
    """aria-current on links to url; is-current on the Services buttons when a Services panel link matched."""
    if not url:
        return h, []
    marked = []
    in_panel = False
    def sub(m):
        nonlocal in_panel
        tag, cls, href = m.group(0), m.group(1) or "", m.group(2)
        if href != url:
            return tag
        if "brand" in cls.split() or "btn-primary" in cls.split():
            return tag
        if any(c in cls.split() for c in ("dd-item", "menu-sub-item")):
            in_panel = True
        marked.append((cls or "nav") + " " + href)
        return tag[:-1] + ' aria-current="page">'
    h = re.sub(r'<a (?:class="([^"]*)" )?href="([^"]*)">', sub, h)
    if in_panel:
        h, n1 = re.subn(r'class="nav-dd-btn"', 'class="nav-dd-btn is-current"', h)
        h, n2 = re.subn(r'class="menu-link menu-sub-btn"', 'class="menu-link menu-sub-btn is-current"', h)
        marked.append(f"is-current on Services buttons ({n1}+{n2})")
    return h, marked


def mark_footer(f, url):
    if not url:
        return f, []
    marked = []
    out = []
    # only the link columns, never the brand link
    parts = re.split(r'(<nav class="footer-col".*?</nav>)', f, flags=re.S)
    for part in parts:
        if part.startswith('<nav class="footer-col"'):
            def sub(m):
                if m.group(1) == url:
                    marked.append("footer " + url)
                    return f'<a href="{url}" aria-current="page">'
                return m.group(0)
            part = re.sub(r'<a href="([^"]*)">', sub, part)
        out.append(part)
    return "".join(out), marked


def resolve(arg):
    p = os.path.realpath(arg if os.path.isabs(arg) else os.path.join(ROOT, arg))
    root = os.path.realpath(ROOT)
    if not p.startswith(root + os.sep):
        return None, "outside the site folder"
    rel = os.path.relpath(p, root)
    # lower case: the Mac disk ignores letter case, so Samples/ is the same folder as samples/
    if rel.split(os.sep)[0].lower() in REFUSE:
        return None, "refused (sample designs and lead mockups are never touched)"
    if not os.path.isfile(p):
        return None, "no such file"
    return rel.replace(os.sep, "/"), None


def main(argv):
    check = "--check" in argv
    src = "index.html"
    if "--source" in argv:
        src = argv[argv.index("--source") + 1]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] == "--source")]
    if "--all" in argv:
        args = MAIN_PAGES + args
    if not args:
        print(__doc__)
        return 2
    srel, err = resolve(src)
    if err:
        print("source", src, err)
        return 2
    with open(os.path.join(ROOT, srel), encoding="utf-8") as fh:
        st = fh.read()
    source = {}
    for k, rx in BLOCKS.items():
        m = rx.findall(st)
        if len(m) != 1:
            print(f"source {srel}: expected one {k} block, found {len(m)}")
            return 2
        source[k] = strip_marks(m[0])
    if "bar-slim" in source["header"]:
        print("source has the slim header; pick a page with the full header")
        return 2
    would_change = False
    for a in args:
        rel, err = resolve(a)
        if err:
            print(f"{a}: {err}")
            would_change = would_change or False
            continue
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            t = fh.read()
        orig = t
        url = url_for(rel)
        mark_url = ALIAS.get(url, url)
        notes, marks = [], []
        for k, rx in BLOCKS.items():
            found = rx.findall(t)
            if len(found) != 1:
                notes.append(f"{k}: {len(found)} found, left alone")
                continue
            cur = found[0]
            if k == "header" and "bar-slim" in cur:
                notes.append("slim header kept")
                continue
            new = source[k]
            if k == "header":
                new, mk = mark_header(new, mark_url)
                marks += mk
            elif k == "footer":
                # the footer marks the real page link (/free-check/ has no footer link; its service does)
                new, mk = mark_footer(new, mark_url)
                marks += mk
            elif k == "fbar" and url == "/get-started/":
                new = new.replace('<a class="btn btn-primary btn-sm" href="/get-started/">', '<a class="btn btn-primary btn-sm" href="#start">')
            if new != cur:
                t = t.replace(cur, new, 1)
                notes.append(f"{k} updated")
        changed = t != orig
        would_change |= changed
        if changed and not check:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(t)
        state = ("would change" if check else "changed") if changed else "unchanged"
        print(f"{rel:46s} {state:12s} {'; '.join(notes) or '-'}")
        print(f"{'':46s} marks: {', '.join(marks) or 'none'}")
    return 1 if (check and would_change) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
