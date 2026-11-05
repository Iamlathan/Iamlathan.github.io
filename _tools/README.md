# _tools

Maintenance scripts for this repo. Folders starting with "_" are not published.

Run the tests from the site folder:

    python3 -m unittest discover -s _tools -p "test_*.py"

`hooks/` holds a pre-commit check. Install it once in each clone:

    bash _tools/hooks/install_hooks.sh

The check needs `_tools/hooks/blocked.private.txt`, which is local only. Without it every commit is refused.
