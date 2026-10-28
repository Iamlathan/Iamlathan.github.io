# scripts

## guard_no_crew.sh
Stops a commit that adds or changes private crew files: anything in a crew, .claude or agents folder, and, outside samples/, any file named like a crew member (judge.png, security-guard.md and so on). Deleting files always passes.

Install it once in each clone of this repo (run inside the clone):

    bash scripts/install_hooks.sh

That adds a pre-commit hook. GitHub Desktop should run the hook too (not checked yet). To test it once, put any file in a crew/ folder, check it in GitHub Desktop and try to commit: the commit should be refused with the guard's message. Then unstage and delete that test file. On a branch without scripts/guard_no_crew.sh the hook does nothing.

The Publish Samples launcher also runs the guard before it commits.
