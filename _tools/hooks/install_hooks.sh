#!/bin/bash
# Installs a pre-commit hook in this clone that runs _tools/hooks/check_private.sh.
# The hook runs the check from whatever branch is checked out. If it is not there, it refuses the commit.
# Works in a normal clone and in a git worktree (hooks live in the shared git folder).
# Safe to run again. It will not replace a pre-commit hook it did not write.
# The check also needs the gitignored _tools/hooks/blocked.private.txt; see _tools/README.md.

MARK="# installed by install_hooks.sh"

top="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "install_hooks: run this inside the site repo"; exit 1; }
cd "$top" || exit 1
hooks="$(git rev-parse --git-path hooks)" || { echo "install_hooks: could not find the hooks folder"; exit 1; }
case "$hooks" in /*) ;; *) hooks="$top/$hooks" ;; esac
mkdir -p "$hooks" || exit 1
hook="$hooks/pre-commit"

if [ -e "$hook" ] && ! grep -q '^# installed by .*install_hooks\.sh' "$hook"; then
  echo "install_hooks: $hook already exists and was not written by this script, so it was left alone."
  echo "Add this line to it by hand instead: /bin/bash \"\$(git rev-parse --show-toplevel)/_tools/hooks/check_private.sh\" || exit 1"
  exit 1
fi

cat > "$hook" <<EOF
#!/bin/sh
$MARK
EOF
cat >> "$hook" <<'EOF'
top="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$top" ]; then
  echo "pre-commit: could not find the repo folder, commit refused"
  exit 1
fi
if [ -f "$top/_tools/hooks/check_private.sh" ]; then
  exec /bin/bash "$top/_tools/hooks/check_private.sh"
fi
echo "pre-commit: commit refused. The check _tools/hooks/check_private.sh is missing from this branch."
echo "Restore it, or check out a branch that has it, and commit again."
exit 1
EOF
chmod +x "$hook" || exit 1
if [ ! -f "$top/_tools/hooks/blocked.private.txt" ]; then
  echo "install_hooks: note, _tools/hooks/blocked.private.txt is missing, so every commit will be refused until you copy it in."
fi
echo "install_hooks: pre-commit hook installed at $hook"
