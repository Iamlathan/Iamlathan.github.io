# _tools

Maintenance scripts for this repo. Folders starting with "_" are not published.

Run the tests from the site folder:

    python3 -m unittest discover -s _tools -p "test_*.py"

`sync_chrome.py` copies the shared header, footer and floating bar from the home page into every main page and sets each page's current link: `python3 _tools/sync_chrome.py --all` (add `--check` to only report what would change).
`blocks_check.py` reads every main page and counts the versions of each shared block (in step is 1 footer, 1 floating bar, and 1 header plus the slim /get-started/ one): `python3 _tools/blocks_check.py`

`strip_css.py` writes a comment free copy of a style file for publishing: `python3 _tools/strip_css.py assets/gcd.css --out FOLDER` (without `--out` it only prints the sizes, raw and gzip level 9). It takes out comments and the lines they leave empty, and copies everything else byte for byte, strings and url(...) values included. The commented file stays the source you edit, and the pages still load assets/gcd.css. The tool refuses to write into the source's own folder.

`make_small_shots.py` makes the 800 px copy of each /work/ card picture for small screens (work/shots/desktop/SLUG-800.webp, from the big file beside it, which is only read): `python3 _tools/make_small_shots.py`, then `python3 _tools/build_pages.py --no-shots` so the cards offer the copies. Run it again after any desktop shot is retaken (the build prints a note), or phones keep the old picture. It needs dwebp and cwebp.

`hooks/` holds a pre-commit check. Install it once in each clone:

    bash _tools/hooks/install_hooks.sh

The check needs `_tools/hooks/blocked.private.txt`, which is local only. Without it every commit is refused.
