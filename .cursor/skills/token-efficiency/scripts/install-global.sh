#!/usr/bin/env bash
#
# Install token-efficiency outside this repository.
#
#   install-global.sh                        install the skill to ~/.cursor/skills
#   install-global.sh --repo ~/code/app ...  also install the always-apply rule into those repos
#   install-global.sh --print-rule           print the User Rules text and exit
#   install-global.sh --no-clipboard         skip copying the rule to the clipboard
#
# Skills in ~/.cursor/skills are loaded in every project, so the skill half is fully
# automatable. Cursor's User Rules are not stored on the filesystem, so the always-on
# half needs one paste into Settings -> Rules -> User Rules; this script puts the text
# on your clipboard so that paste is all that is left. Use --repo for repositories
# where you would rather commit the rule as a project rule.
set -euo pipefail

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_name="$(basename "$skill_dir")"
bundled_rule="$skill_dir/assets/user-rule.md"
project_rule="$skill_dir/../../rules/token-efficiency.mdc"

repos=()
use_clipboard=1
print_only=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "--repo needs a path" >&2; exit 2; }
      repos+=("$2"); shift 2 ;;
    --no-clipboard) use_clipboard=0; shift ;;
    --print-rule) print_only=1; shift ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

strip_frontmatter() {
  awk 'NR==1 && $0=="---" { in_fm=1; next }
       in_fm && $0=="---" { in_fm=0; next }
       in_fm { next }
       { print }' "$1"
}

# The .mdc is the source of truth when running from a checkout; the bundled asset keeps
# a globally installed copy able to reprint the rule on its own.
rule_text() {
  if [[ -f "$project_rule" ]]; then
    strip_frontmatter "$project_rule" | sed '/./,$!d'
  else
    cat "$bundled_rule"
  fi
}

if [[ ! -f "$project_rule" && ! -f "$bundled_rule" ]]; then
  echo "error: found neither $project_rule nor $bundled_rule" >&2
  exit 1
fi

if [[ $print_only -eq 1 ]]; then
  rule_text
  exit 0
fi

if [[ -f "$project_rule" && -f "$bundled_rule" ]] \
   && ! diff -q <(rule_text) "$bundled_rule" >/dev/null; then
  echo "warning: assets/user-rule.md has drifted from token-efficiency.mdc;" >&2
  echo "         using the .mdc. Refresh with: $0 --print-rule > $bundled_rule" >&2
fi

dest="$HOME/.cursor/skills/$skill_name"
mkdir -p "$(dirname "$dest")"
rm -rf "$dest"
cp -R "$skill_dir" "$dest"
echo "Skill installed: $dest (available in every project)"

for repo in "${repos[@]}"; do
  if [[ ! -d "$repo" ]]; then
    echo "warning: skipping --repo $repo (not a directory)" >&2
    continue
  fi
  mkdir -p "$repo/.cursor/rules"
  if [[ -f "$project_rule" ]]; then
    cp "$project_rule" "$repo/.cursor/rules/token-efficiency.mdc"
  else
    { printf -- '---\ndescription: Context and token discipline applied to every request.\nalwaysApply: true\n---\n\n'
      cat "$bundled_rule"; } > "$repo/.cursor/rules/token-efficiency.mdc"
  fi
  echo "Rule installed: $repo/.cursor/rules/token-efficiency.mdc (commit it to share)"
done

copied=""
if [[ $use_clipboard -eq 1 ]]; then
  for tool in pbcopy wl-copy "xclip -selection clipboard" "xsel --clipboard --input"; do
    cmd="${tool%% *}"
    command -v "$cmd" >/dev/null 2>&1 || continue
    if rule_text | $tool 2>/dev/null; then copied="$cmd"; break; fi
  done
fi

echo
if [[ -n "$copied" ]]; then
  echo "Rule text copied to your clipboard via $copied. One step left:"
  echo "  Cursor Settings -> Rules -> User Rules -> paste -> save"
  echo "That scope applies to every repository on this machine."
else
  echo "Last step: paste the text below into Cursor Settings -> Rules -> User Rules,"
  echo "which applies to every repository on this machine."
  echo "(Reprint any time with: $dest/scripts/install-global.sh --print-rule)"
  echo
  echo "----------------------------------------------------------------------"
  rule_text
fi
