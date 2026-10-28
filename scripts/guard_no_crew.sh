#!/bin/bash
# Refuses a commit that adds or changes private crew files in this public site repo.
# Run by the pre-commit hook (see scripts/install_hooks.sh) and by the Publish Samples launcher.
# Checks only staged paths that are added, copied, changed, renamed or type changed. Deletions always pass.
# Refused:
#   1. any path inside a folder named crew, .claude or agents, at any depth
#   2. outside samples/, a file whose name (without extension) is a crew member slug
# Matching ignores case, and spaces or underscores count as hyphens (Security_Guard.PNG is refused).
# Plain bash 3.2, no reads outside this repo.

# Byte by byte text handling, so a name that is not valid UTF-8 cannot cut tr short and slip through.
export LC_ALL=C

SLUGS="judge builder debugger reviewer security-guard web-designer monitor-bot null totality scout voice watcher backtester believer skeptic investor analyst director operator starlite"

LIST="$(mktemp "${TMPDIR:-/tmp}/guard_no_crew.XXXXXX")" || { echo "guard_no_crew: could not make a temp file, commit refused"; exit 1; }
trap 'rm -f "$LIST"' EXIT

if ! git -c core.quotePath=false diff --cached --name-only -z --diff-filter=ACMRT > "$LIST"; then
  echo "guard_no_crew: could not list the staged files, commit refused"
  exit 1
fi

BAD=""
while IFS= read -r -d '' p; do
  [ -z "$p" ] && continue
  low="$(printf '%s' "$p" | tr 'A-Z' 'a-z')"
  why=""
  case "/$low" in
    */crew/*) why="inside a crew folder" ;;
    */.claude/*) why="inside a .claude folder" ;;
    */agents/*) why="inside an agents folder" ;;
  esac
  if [ -z "$why" ]; then
    case "$low" in
      samples/*) ;;
      *)
        name="${low##*/}"
        name="$(printf '%s' "$name" | tr ' _' '--')"
        one="${name%.*}"
        first="${name%%.*}"
        for s in $SLUGS; do
          if [ "$one" = "$s" ] || [ "$first" = "$s" ]; then
            why="named like crew member $s (only allowed under samples/)"
            break
          fi
        done
        ;;
    esac
  fi
  [ -n "$why" ] && BAD="$BAD
  $p  ($why)"
done < "$LIST"

if [ -n "$BAD" ]; then
  echo "guard_no_crew: commit refused. Crew files are private and must not go on the public site:$BAD"
  echo "Unstage them (git restore --staged <path>, or uncheck them in GitHub Desktop) and commit again."
  exit 1
fi
exit 0
