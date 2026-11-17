#!/usr/bin/env python3
"""Write a comment free copy of a style file for publishing. The commented source is never changed.

usage (from the site folder):
  python3 _tools/strip_css.py assets/gcd.css                    print the sizes only, write nothing
  python3 _tools/strip_css.py assets/gcd.css --out FOLDER       also write FOLDER/gcd.css
  python3 _tools/strip_css.py FILE [FILE ...] [--out FOLDER]    more than one file in one run

What it does:
- Takes out every /* comment */ and nothing else. Strings ("..." and '...'), url(...) values and escapes
  (a backslash and the character after it) are copied byte for byte, even when they hold /* or */.
- A line left empty by a comment goes, and so do the spaces a comment leaves at the end of a line.
  Blank lines that were in the source stay.
- Where taking a comment out would join two pieces of code into a different one (div/**/p, 1/**/px), an empty
  /**/ stays in its place, so the rules read exactly as before.
- Prints the size before and after, raw and gzip level 9, and how many comments went.
- Refuses to write into the folder a source file sits in (by any path to it), refuses a link or a source file
  already sitting in the --out folder under a copy's name, refuses two sources with the same file name, and
  writes nothing if any file has an unclosed comment, string or url(. All of these are checked before any
  folder is made or any file is written.
"""
import argparse
import gzip
import os
import sys

# Next to these a comment can go with nothing in its place: they always end or start a token of their own.
SAFE = set(" \t\n\r\f{};,:")
SAFE_LEFT = SAFE | set("([")
SAFE_RIGHT = SAFE | set(")]")


def is_name_char(c):
    return c.isascii() and (c.isalnum() or c in "_-") or not c.isascii()


def line_of(text, i):
    return text.count("\n", 0, i) + 1


def strip_comments(text):
    """Return (stripped text, comments removed, empty /**/ kept). Raises ValueError on an unclosed comment,
    string or url(."""
    out = []
    n = len(text)
    i = 0
    escape_end = -1
    removed = kept = 0
    while i < n:
        c = text[i]
        if c == "\\":
            out.extend(text[i:i + 2])
            escape_end = len(out)
            i += 2
            continue
        if c in "\"'":
            j = i + 1
            while True:
                if j >= n or text[j] in "\n\r\f":
                    raise ValueError("unclosed string at line %d" % line_of(text, i))
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == c:
                    break
                j += 1
            out.extend(text[i:j + 1])
            i = j + 1
            continue
        if c in "uU" and text[i:i + 4].lower() == "url(" and (i == 0 or not is_name_char(text[i - 1])):
            j = i + 4
            while j < n and text[j] in " \t\n\r\f":
                j += 1
            if j < n and text[j] in "\"'":
                out.extend(text[i:j])
                i = j
                continue
            while j < n and text[j] != ")":
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise ValueError("unclosed url( at line %d" % line_of(text, i))
            out.extend(text[i:j + 1])
            i = j + 1
            continue
        if c == "/" and text[i + 1:i + 2] == "*":
            j = i
            while text.startswith("/*", j):
                end = text.find("*/", j + 2)
                if end < 0:
                    raise ValueError("unclosed comment at line %d" % line_of(text, j))
                removed += 1
                j = end + 2
            right = text[j] if j < n else ""
            if right in ("", "\n", "\r"):
                while out and out[-1] in " \t\f":
                    out.pop()
                if not out or out[-1] in "\n\r":
                    if text.startswith("\r\n", j):
                        j += 2
                    elif right:
                        j += 1
            else:
                left = out[-1] if out else ""
                left_safe = left == "" or (left in SAFE_LEFT and len(out) != escape_end)
                if not (left_safe or right in SAFE_RIGHT):
                    out.extend("/**/")
                    kept += 1
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out), removed, kept


def gz_size(data):
    return len(gzip.compress(data, compresslevel=9, mtime=0))


def out_problem(out, files):
    """Why writing the copies into the folder out could touch a source file, or None. Every path is resolved
    first (a folder that does not exist yet, '..', links, and letter case on the Mac disk), and this runs before
    any folder is made or any file is written."""
    out_real = os.path.realpath(out)
    for path in files:
        if os.path.isdir(out_real) and os.path.samefile(out_real, os.path.dirname(os.path.abspath(path))):
            return "--out %s is the folder of the source %s; pick another folder" % (out, path)
    for path in files:
        dest = os.path.join(out_real, os.path.basename(path))
        if os.path.islink(dest):
            return "%s is a link, which could lead to a source file; move it away or pick another folder" % dest
        if os.path.exists(dest) and any(os.path.samefile(dest, p) for p in files):
            return "%s is the same file as a source; pick another folder" % dest
    return None


def main(argv):
    ap = argparse.ArgumentParser(prog="strip_css.py", description="Write a comment free copy of a style file.")
    ap.add_argument("files", nargs="+", metavar="FILE")
    ap.add_argument("--out", metavar="FOLDER", help="folder for the stripped copies (default: print sizes only)")
    args = ap.parse_args(argv)

    names = {}
    for path in args.files:
        name = os.path.basename(path)
        if name in names:
            print("strip_css: %s and %s have the same name; run them one at a time" % (names[name], path),
                  file=sys.stderr)
            return 2
        names[name] = path
    if args.out:
        problem = out_problem(args.out, args.files)
        if problem:
            print("strip_css: " + problem, file=sys.stderr)
            return 2

    results = []
    for path in args.files:
        try:
            with open(path, encoding="utf-8", newline="") as f:
                src = f.read()
            stripped, removed, kept = strip_comments(src)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            print("strip_css: %s: %s" % (path, e), file=sys.stderr)
            return 2
        results.append((path, src, stripped, removed, kept))

    for path, src, stripped, removed, kept in results:
        a, b = src.encode("utf-8"), stripped.encode("utf-8")
        ga, gb = gz_size(a), gz_size(b)
        print("%s: raw %d -> %d bytes (%.1f%% smaller), gzip -9 %d -> %d bytes (%.1f%% smaller), "
              "%d comments removed, %d empty /**/ kept" % (path, len(a), len(b), 100.0 * (len(a) - len(b)) / len(a),
                                                           ga, gb, 100.0 * (ga - gb) / ga, removed, kept))
    if args.out:
        out_real = os.path.realpath(args.out)
        try:
            os.makedirs(out_real, exist_ok=True)
            for path, _, stripped, _, _ in results:
                dest = os.path.join(out_real, os.path.basename(path))
                # O_NOFOLLOW: never write through a link, even one made after the checks above
                fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                    f.write(stripped)
                print("wrote %s" % dest)
        except OSError as e:
            print("strip_css: could not write the copy: %s" % e, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
