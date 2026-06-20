#!/usr/bin/env bash
# Install the Prism skills (blueprint + replay) without the plugin system.
# Copies each self-contained skill into your Claude skills directory.
#
#   ./install.sh                 # user-level: ~/.claude/skills
#   ./install.sh ./project       # project-level: ./project/.claude/skills
#   ./install.sh /custom/path    # any skills dir
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

arg="${1:-$HOME/.claude/skills}"
# if given a project dir, target its .claude/skills
if [ -d "$arg" ] && [ "$(basename "$arg")" != "skills" ]; then
  DEST="$arg/.claude/skills"
else
  DEST="$arg"
fi
mkdir -p "$DEST"

for s in blueprint replay; do
  rm -rf "${DEST:?}/$s"
  cp -R "$HERE/skills/$s" "$DEST/$s"
  echo "  installed $s -> $DEST/$s"
done

echo "Done. Run /skills in Claude Code (or restart it) to pick them up."
