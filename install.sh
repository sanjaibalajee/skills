#!/usr/bin/env bash
# Install skills from this repo without npx or the plugin system.
# Every folder under skills/ that has a SKILL.md is a skill.
#
#   ./install.sh                         # all skills -> ~/.claude/skills
#   ./install.sh unslop plan-doc         # just these
#   ./install.sh --project ~/code/app    # -> ~/code/app/.claude/skills
#   ./install.sh --dest ~/.agents/skills # any skills dir (Codex, others)
#   ./install.sh --link unslop           # symlink instead of copy (edit here, use everywhere)
#   ./install.sh --list                  # show what's available
#   ./install.sh --remove unslop         # uninstall from the target dir
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/skills"

usage() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

available() {
  for d in "$SRC"/*/; do
    [ -f "$d/SKILL.md" ] && basename "$d"
  done
}

describe() {  # first line of the frontmatter description, trimmed for a terminal
  sed -n 's/^description: "\{0,1\}//p' "$SRC/$1/SKILL.md" | head -1 | cut -c1-90
}

DEST="$HOME/.claude/skills"
MODE=copy
ACTION=install
picked=()

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    -l|--list) ACTION=list ;;
    --remove) ACTION=remove ;;
    --link) MODE=link ;;
    --dest) DEST="${2:?--dest needs a directory}"; shift ;;
    --project) DEST="${2:?--project needs a directory}/.claude/skills"; shift ;;
    -*) echo "unknown option: $1" >&2; usage 2 ;;
    *)
      # Older usage passed a target dir as the only argument; keep that working.
      if [ -d "$1" ] && [ ! -f "$SRC/$1/SKILL.md" ]; then
        if [ "$(basename "$1")" = "skills" ]; then DEST="$1"; else DEST="$1/.claude/skills"; fi
      else
        picked+=("$1")
      fi ;;
  esac
  shift
done

if [ "$ACTION" = list ]; then
  for s in $(available); do printf '  %-12s %s\n' "$s" "$(describe "$s")"; done
  exit 0
fi

[ ${#picked[@]} -eq 0 ] && while IFS= read -r s; do picked+=("$s"); done < <(available)

for s in "${picked[@]}"; do
  if [ ! -f "$SRC/$s/SKILL.md" ]; then
    echo "no such skill: $s (try --list)" >&2
    exit 1
  fi
done

mkdir -p "$DEST"
for s in "${picked[@]}"; do
  target="$DEST/$s"
  if [ "$ACTION" = remove ]; then
    rm -rf "${target:?}"
    echo "  removed $s from $DEST"
    continue
  fi
  rm -rf "${target:?}"
  if [ "$MODE" = link ]; then
    ln -s "$SRC/$s" "$target"
    echo "  linked    $s -> $target"
  else
    cp -R "$SRC/$s" "$target"
    echo "  installed $s -> $target"
  fi
done

[ "$ACTION" = install ] && echo "Done. Run /skills in Claude Code (or restart it) to pick them up."
exit 0
