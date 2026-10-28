#!/bin/bash
# Installs a pre-commit hook in this clone that runs scripts/guard_no_crew.sh.
# The hook runs the guard from whatever branch is checked out, and quietly passes
# on a branch that does not have the guard yet, so other branches keep working.
# Works in a normal clone and in a git worktree (hooks live in the shared git folder).
# Safe to run again. It will not replace a pre-commit hook it did not write.

MARK="# installed by scripts/install_hooks.sh (guard_no_crew)"

top="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "install_hooks: run this inside the site repo"; exit 1; }
cd "$top" || exit 1
hooks="$(git rev-parse --git-path hooks)" || { echo "install_hooks: could not find the hooks folder"; exit 1; }
case "$hooks" in /*) ;; *) hooks="$top/$hooks" ;; esac
mkdir -p "$hooks" || exit 1
hook="$hooks/pre-commit"

if [ -e "$hook" ] && ! grep -qF "$MARK" "$hook"; then
  echo "install_hooks: $hook already exists and was not written by this script, so it was left alone."
  echo "Add this line to it by hand instead: /bin/bash \"\$(git rev-parse --show-toplevel)/scripts/guard_no_crew.sh\" || exit 1"
  exit 1
fi

cat > "$hook" <<EOF
#!/bin/sh
$MARK
top="\$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -f "\$top/scripts/guard_no_crew.sh" ] || exit 0
exec /bin/bash "\$top/scripts/guard_no_crew.sh"
EOF
chmod +x "$hook" || exit 1
echo "install_hooks: pre-commit hook installed at $hook"
