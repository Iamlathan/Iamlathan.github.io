#!/bin/bash
# Refuses a commit that adds or changes private files in this public site repo.
# Run by the pre-commit hook (see _tools/hooks/install_hooks.sh). See _tools/README.md.
# Checks only staged paths that are added, copied, changed, renamed or type changed. Deletions always pass.
# The blocked names live in the gitignored _tools/hooks/blocked.private.txt (one per line, # comments):
#   dir: <name>   refuse any path inside a folder with that name, at any depth
#   <name>        outside samples/, refuse a file whose name (without extension) is that name
# The private list itself is always refused. If the list is missing, unreadable or has no entries,
# every commit is refused (fail closed).
# Matching ignores case and leading dots, and spaces or underscores count as hyphens
# (Some_Name.PNG and .some-name.md match some-name).
# Plain bash 3.2, no reads outside this repo.

# Byte by byte text handling, so a name that is not valid UTF-8 cannot cut tr short and slip through.
export LC_ALL=C

LIST_REL="_tools/hooks/blocked.private.txt"

top="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$top" ]; then
  echo "check_private: not inside a git repo, commit refused"
  exit 1
fi
LIST_FILE="$top/$LIST_REL"
if [ ! -f "$LIST_FILE" ] || [ ! -r "$LIST_FILE" ]; then
  echo "check_private: commit refused. The private block list $LIST_REL is missing or unreadable."
  echo "Copy it back in from your private copy (it is gitignored, so a fresh clone does not have it), then commit again."
  exit 1
fi

# Normalize the list: lower case, CR and spaces trimmed, comments and blank lines dropped,
# spaces or underscores in names read as hyphens. Folder names go to DIRS, file names to NAMES.
DIRS=""
NAMES=""
while IFS= read -r line || [ -n "$line" ]; do
  line="$(printf '%s' "$line" | tr -d '\r' | tr 'A-Z' 'a-z' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  case "$line" in
    ''|'#'*) continue ;;
    dir:*)
      d="$(printf '%s' "${line#dir:}" | sed -e 's/^[[:space:]]*//')"
      case "$d" in ''|*/*) continue ;; esac
      DIRS="$DIRS$d
"
      ;;
    *)
      n="$(printf '%s' "$line" | tr ' _' '--')"
      NAMES="$NAMES$n
"
      ;;
  esac
done < "$LIST_FILE"

if [ -z "$DIRS$NAMES" ]; then
  echo "check_private: commit refused. The private block list $LIST_REL has no entries."
  exit 1
fi

STAGED="$(mktemp "${TMPDIR:-/tmp}/check_private.XXXXXX")" || { echo "check_private: could not make a temp file, commit refused"; exit 1; }
trap 'rm -f "$STAGED"' EXIT

if ! git -c core.quotePath=false diff --cached --name-only -z --diff-filter=ACMRT > "$STAGED"; then
  echo "check_private: could not list the staged files, commit refused"
  exit 1
fi

LIST_LOW="$(printf '%s' "$LIST_REL" | tr 'A-Z' 'a-z')"
BAD=""
while IFS= read -r -d '' p; do
  [ -z "$p" ] && continue
  low="$(printf '%s' "$p" | tr 'A-Z' 'a-z')"
  why=""
  if [ "$low" = "$LIST_LOW" ]; then
    why="the private block list"
  fi
  if [ -z "$why" ]; then
    while IFS= read -r d; do
      [ -z "$d" ] && continue
      case "/$low" in
        */"$d"/*) why="inside a blocked folder"; break ;;
      esac
    done <<EOF
$DIRS
EOF
  fi
  if [ -z "$why" ]; then
    case "$low" in
      samples/*) ;;
      *)
        name="${low##*/}"
        name="$(printf '%s' "$name" | tr ' _' '--')"
        # Hidden files: drop every leading dot, so .some-name.md is checked as some-name.md.
        while [ "${name#.}" != "$name" ]; do
          name="${name#.}"
        done
        one="${name%.*}"
        first="${name%%.*}"
        while IFS= read -r s; do
          [ -z "$s" ] && continue
          if [ "$one" = "$s" ] || [ "$first" = "$s" ]; then
            why="file name on the private block list (only allowed under samples/)"
            break
          fi
        done <<EOF
$NAMES
EOF
        ;;
    esac
  fi
  [ -n "$why" ] && BAD="$BAD
  $p  ($why)"
done < "$STAGED"

if [ -n "$BAD" ]; then
  echo "check_private: commit refused. These files are private and must not go on the public site:$BAD"
  echo "Unstage them (git restore --staged <path>, or uncheck them in GitHub Desktop) and commit again."
  exit 1
fi
exit 0
