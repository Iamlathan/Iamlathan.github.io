#!/usr/bin/env python3
"""Make the 800 px copies of the /work/ card pictures, for small and low density screens:
work/shots/desktop/<slug>-800.webp from work/shots/desktop/<slug>.webp.

Run from the site folder, after any desktop shot is taken or retaken, then build /work/ again:
  python3 _tools/make_small_shots.py              every desktop shot
  python3 _tools/make_small_shots.py SLUG SLUG    only these

The big files are only read, never written. A copy is always made from the big file on disk, so it is the same
picture, and an older copy is replaced. A file in the way that is not 800 px wide is left alone and reported.
Needs dwebp and cwebp (the webp tools from Homebrew). See _tools/README.md.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402

SUFFIX = "-%d" % bp.SMALL_SHOT_W
# Highest quality first; the first one at or under the cap is kept (the last one when none fits).
SMALL_QUALITIES = (82, 78, 74, 70)
SMALL_MAX_BYTES = 60 * 1000
TOOL_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")


def find_tools():
    """(dwebp, cwebp) full paths, or None when either is missing."""
    found = []
    for name in ("dwebp", "cwebp"):
        path = shutil.which(name) or next((os.path.join(d, name) for d in TOOL_DIRS
                                           if os.access(os.path.join(d, name), os.X_OK)), None)
        if not path:
            return None
        found.append(path)
    return tuple(found)


def big_shots():
    """Slugs of the desktop shots on disk, sorted. Files named <something>-800.webp are copies, never sources."""
    if not os.path.isdir(bp.DESKTOP_SHOTS):
        return []
    return sorted(n[:-5] for n in os.listdir(bp.DESKTOP_SHOTS)
                  if n.endswith(".webp") and bp.SLUG_RE.fullmatch(n[:-5]) and not n[:-5].endswith(SUFFIX)
                  and os.path.isfile(os.path.join(bp.DESKTOP_SHOTS, n)))


def make_small(slug, tools):
    """Make one copy. Returns (ok, report line)."""
    dwebp, cwebp = tools
    src = os.path.join(bp.DESKTOP_SHOTS, slug + ".webp")
    out = bp.small_shot(slug)
    size = bp.image_size(src)
    if not size:
        return False, "%s cannot be read as WebP, no copy made" % bp.rel(src)
    if size[0] <= bp.SMALL_SHOT_W:
        return True, "%s is %d px wide, so it needs no copy" % (bp.rel(src), size[0])
    if os.path.lexists(out):
        there = bp.image_size(out) if os.path.isfile(out) and not os.path.islink(out) else None
        if not there or there[0] != bp.SMALL_SHOT_W:
            return False, "%s is not an 800 px copy (%s), left alone" % (
                bp.rel(out), "%d px wide" % there[0] if there else "not a readable WebP file")
    with tempfile.TemporaryDirectory(prefix="gcd-small-") as tmp:
        png, trial = os.path.join(tmp, "big.png"), os.path.join(tmp, "small.webp")
        try:
            subprocess.run([dwebp, "-quiet", src, "-o", png], check=True, capture_output=True, timeout=120)
            for q in SMALL_QUALITIES:
                subprocess.run([cwebp, "-quiet", "-q", str(q), "-m", "6", "-sharp_yuv",
                                "-resize", str(bp.SMALL_SHOT_W), "0", png, "-o", trial],
                               check=True, capture_output=True, timeout=120)
                if os.path.getsize(trial) <= SMALL_MAX_BYTES:
                    break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            return False, "%s: the webp tools failed (%s), no copy made" % (bp.rel(src), type(e).__name__)
        made = bp.image_size(trial)
        if not made or made[0] != bp.SMALL_SHOT_W:
            return False, "%s: the copy did not come out 800 px wide, nothing written" % bp.rel(src)
        with open(trial, "rb") as f:
            data = f.read()
    bp.write_atomic(out, data)
    line = "%s: %d x %d, q%d, %d KB" % (bp.rel(out), made[0], made[1], q, round(len(data) / 1000))
    if len(data) > SMALL_MAX_BYTES:
        line += " (OVER %d KB at the lowest quality tried)" % (SMALL_MAX_BYTES // 1000)
    return True, line


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make the 800 px copies of the /work/ desktop shots.")
    ap.add_argument("slugs", nargs="*", help="only these desktop shots (default: all of them)")
    args = ap.parse_args(argv)
    tools = find_tools()
    if not tools:
        print("STOPPED, nothing written: this needs dwebp and cwebp (brew install webp)")
        return 2
    have = big_shots()
    problems = 0
    for slug in args.slugs:
        if slug not in have:
            print("PROBLEM: no desktop shot named %r in %s" % (slug, bp.rel(bp.DESKTOP_SHOTS)))
            problems += 1
    for slug in ([s for s in have if s in args.slugs] if args.slugs else have):
        ok, line = make_small(slug, tools)
        print(line if ok else "PROBLEM: " + line)
        problems += 0 if ok else 1
    if not have:
        print("No desktop shots in %s yet." % bp.rel(bp.DESKTOP_SHOTS))
    print("\nRESULT: %s" % ("OK. Now run python3 _tools/build_pages.py --no-shots so /work/ offers the copies."
                            if not problems else "%d problem(s)" % problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
