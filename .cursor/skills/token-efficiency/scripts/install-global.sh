#!/usr/bin/env bash
# Install the token-efficiency skill into ~/.cursor/skills so it is available in every
# repository, and print the always-on rule for pasting into User Rules.
set -euo pipefail

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rule_file="$(cd "$skill_dir/../../rules" && pwd)/token-efficiency.mdc"
dest="$HOME/.cursor/skills/token-efficiency"

mkdir -p "$(dirname "$dest")"
rm -rf "$dest"
cp -R "$skill_dir" "$dest"
echo "Installed skill to $dest"

cat <<'EOF'

The skill is now global. The always-apply rule is per-project, so to get the same
always-on behavior everywhere, copy the text below into:

  Cursor Settings -> Rules -> User Rules

(Strip the YAML frontmatter between the --- markers; User Rules are plain text.)

----------------------------------------------------------------------
EOF

cat "$rule_file"
