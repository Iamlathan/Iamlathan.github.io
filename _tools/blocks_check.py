#!/usr/bin/env python3
"""Proof: header, footer and floating bar are the same on every main page once the current page marks are taken out.
Reads only; it never writes a page.
usage (from the site folder): python3 _tools/blocks_check.py [extra pages...]
With no arguments it checks every page in sync_chrome.MAIN_PAGES. Pages are paths inside the site folder.
In step means 1 footer variant, 1 floating bar variant and 2 header variants (the full one, and the slim one
on get-started/index.html only). Fix a stray page with:  python3 _tools/sync_chrome.py PAGE"""
import hashlib, re, sys
import sync_chrome as s
pages = s.MAIN_PAGES + sys.argv[1:]
for k, rx in s.BLOCKS.items():
    groups = {}
    for p in pages:
        with open(s.ROOT + "/" + p, encoding="utf-8") as fh:
            t = fh.read()
        m = rx.findall(t)
        b = s.strip_marks(m[0]) if len(m) == 1 else "MISSING %d" % len(m)
        if k == "fbar":
            b = b.replace('href="#start"', 'href="/get-started/"')
        groups.setdefault(hashlib.sha1(b.encode()).hexdigest()[:10], []).append(p)
    print(f"{k}: {len(groups)} variant(s)")
    for h, ps in groups.items():
        print("   ", h, len(ps), ps if len(ps) < 4 else ps[:2] + ["..."])
