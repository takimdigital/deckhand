#!/usr/bin/env sh
# Deckhand installer — copies (or links) skills/deckhand into every agent harness it finds,
# and puts a `dh` shim in ~/.deckhand/bin.  Usage:
#   ./install.sh                  # every detected harness
#   ./install.sh --link           # symlink instead of copy (git pull updates every harness)
#   ./install.sh --only claude,hermes
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/skills/deckhand"
MODE=copy; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --link) MODE=link ;;
    --only) ONLY="$2"; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
  esac; shift
done

say() { printf '%s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { say "missing: $1 ($2)"; MISSING=1; }; }
MISSING=0
need python3 "Python 3.9+ runs the dh control plane"
need node "Node 18+ runs try-on and compose"
need git "git clones bases and versions projects"
[ "$MISSING" = 1 ] && say "(install what is missing, then re-run — nothing else is required)"

HOMES="claude:$HOME/.claude/skills
codex:$HOME/.codex/skills
agents:$HOME/.agents/skills
cursor:$HOME/.cursor/skills
hermes:$HOME/.hermes/skills
hermes:$HOME/.local/share/hermes/skills
opencode:$HOME/.config/opencode/skills
gemini:$HOME/.gemini/skills"

installed=""
echo "$HOMES" | while IFS=: read -r name dir; do
  parent=$(dirname "$dir")
  if [ -n "$ONLY" ] && ! echo ",$ONLY," | grep -q ",$name,"; then continue; fi
  [ -d "$parent" ] || [ "$name" = "agents" ] || continue
  mkdir -p "$dir"
  rm -rf "$dir/deckhand"
  if [ "$MODE" = link ]; then ln -s "$SRC" "$dir/deckhand"; else cp -R "$SRC" "$dir/deckhand"; fi
  say "✓ $name → $dir/deckhand ($MODE)"
done

# a stable home for the shim (survives deleting the clone in copy mode)
mkdir -p "$HOME/.deckhand/bin" "$HOME/.deckhand/skill"
rm -rf "$HOME/.deckhand/skill/deckhand"
if [ "$MODE" = link ]; then ln -s "$SRC" "$HOME/.deckhand/skill/deckhand"; else cp -R "$SRC" "$HOME/.deckhand/skill/deckhand"; fi
cat > "$HOME/.deckhand/bin/dh" <<SHIM
#!/usr/bin/env sh
exec python3 "$HOME/.deckhand/skill/deckhand/dh.py" "\$@"
SHIM
chmod +x "$HOME/.deckhand/bin/dh"
say "✓ dh shim → $HOME/.deckhand/bin/dh   (add to PATH: export PATH=\"\$HOME/.deckhand/bin:\$PATH\")"
say ""
say "Next: open your agent and say — \"Create my deckhand profile\", then \"Build me <your business>\"."
