#!/usr/bin/env bash
#
# Install token-efficiency outside this repository.
#
#   install-global.sh                        install the skill for every project
#   install-global.sh --repo ~/code/app ...  also install the always-apply rule into those repos
#   install-global.sh --dest /mnt/c/Users/me treat DIR as an extra home directory to install into
#   install-global.sh --verify               report what is installed where, then exit
#   install-global.sh --print-rule           print the User Rules text and exit
#   install-global.sh --no-clipboard         skip copying the rule to the clipboard
#
# Skills in <home>/.cursor/skills are loaded in every project, so the skill half is
# fully automatable. Cursor's User Rules are not stored on the filesystem, so the
# always-on half needs one paste into Customize -> Rules in the sidebar; this script
# puts the text on your clipboard so that paste is all that is left. Use --repo for
# repositories where you would rather commit the rule as a project rule.
#
# Under WSL the script also installs into the Windows user profile, because Cursor
# running on Windows reads that home rather than the Linux one.
set -euo pipefail

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_name="$(basename "$skill_dir")"
bundled_rule="$skill_dir/assets/user-rule.md"
project_rule="$skill_dir/../../rules/token-efficiency.mdc"

repos=()
extra_homes=()
use_clipboard=1
print_only=0
verify_only=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "--repo needs a path" >&2; exit 2; }
      repos+=("$2"); shift 2 ;;
    --dest)
      [[ $# -ge 2 ]] || { echo "--dest needs a path" >&2; exit 2; }
      extra_homes+=("$2"); shift 2 ;;
    --no-clipboard) use_clipboard=0; shift ;;
    --print-rule) print_only=1; shift ;;
    --verify) verify_only=1; shift ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
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
# an installed copy able to reprint the rule on its own.
rule_text() {
  if [[ -f "$project_rule" ]]; then
    strip_frontmatter "$project_rule" | sed '/./,$!d'
  else
    cat "$bundled_rule"
  fi
}

is_wsl() {
  [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi microsoft /proc/version 2>/dev/null
}

# Cursor on Windows reads the Windows profile, not the WSL home, so a script run inside
# WSL that only writes to $HOME installs somewhere Cursor will never look.
windows_home() {
  local raw win
  is_wsl || return 1
  command -v wslpath >/dev/null 2>&1 || return 1
  command -v cmd.exe >/dev/null 2>&1 || return 1
  raw="$(cd / && cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r\n')" || return 1
  [[ -n "$raw" ]] || return 1
  win="$(wslpath -u "$raw" 2>/dev/null)" || return 1
  [[ -d "$win" ]] || return 1
  printf '%s\n' "$win"
}

homes=("$HOME")
if win_home="$(windows_home)"; then
  homes+=("$win_home")
fi
homes+=("${extra_homes[@]+"${extra_homes[@]}"}")

warn_odd_home() {
  if [[ "$HOME" == "/root" || "$HOME" == "/var/root" ]]; then
    echo "warning: HOME is $HOME, which usually means this ran under sudo." >&2
    echo "         Cursor reads your own home directory. Re-run without sudo." >&2
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

# Distinguishes "installed for every project" from "only visible in the repo that
# contains it", which is the usual reason a skill shows in one Cursor window but not
# another.
verify() {
  local ok=1 home skill declared
  echo "HOME resolves to: $HOME"
  is_wsl && echo "WSL detected: Cursor on Windows reads the Windows profile, not this home."
  echo

  echo "Global skill (loads in every project):"
  for home in "${homes[@]}"; do
    skill="$home/.cursor/skills/$skill_name/SKILL.md"
    if [[ -f "$skill" ]]; then
      declared="$(awk -F': *' '/^name:/ { print $2; exit }' "$skill")"
      if [[ "$declared" == "$skill_name" ]]; then
        echo "  OK   $skill"
        ok=0
      else
        echo "  FAIL $skill declares name '$declared', which must match folder '$skill_name'"
      fi
    else
      echo "  --   nothing at $home/.cursor/skills/$skill_name/"
    fi
  done
  [[ $ok -eq 0 ]] || echo "       run this script with no arguments to install it"

  echo
  echo "Other directories Cursor loads skills from:"
  local d found=0
  for home in "${homes[@]}"; do
    for d in "$home/.agents/skills" "$home/.claude/skills" "$home/.codex/skills"; do
      [[ -d "$d/$skill_name" ]] && { echo "  also present: $d/$skill_name"; found=1; }
    done
  done
  [[ $found -eq 0 ]] && echo "  none (fine - .cursor/skills is enough)"

  echo
  echo "This checkout ($PWD):"
  local here="$PWD/.cursor/skills/$skill_name/SKILL.md" same_as_global=0
  for home in "${homes[@]}"; do
    if [[ -f "$here" && "$here" -ef "$home/.cursor/skills/$skill_name/SKILL.md" ]]; then
      same_as_global=1
    fi
  done
  if [[ $same_as_global -eq 1 ]]; then
    echo "  running from a home directory - the .cursor/skills here IS the global"
    echo "  install reported above, not a separate project copy"
  elif [[ -f "$here" ]]; then
    echo "  project skill present - visible in THIS project only"
  else
    echo "  no project skill here"
  fi
  if [[ -f "$PWD/.cursor/rules/token-efficiency.mdc" ]]; then
    echo "  project rule present - always-on in THIS project only"
  else
    echo "  no project rule here"
  fi

  echo
  echo "Not checkable from a script:"
  echo "  - User Rules live in Cursor's settings, not on disk. Confirm in Customize -> Rules."
  echo "  - Skills are discovered when Cursor starts. Quit Cursor fully and reopen,"
  echo "    then look in Customize -> Skills."
  warn_odd_home
  return $ok
}

if [[ $verify_only -eq 1 ]]; then
  verify
  exit $?
fi

if [[ -f "$project_rule" && -f "$bundled_rule" ]] \
   && ! diff -q <(rule_text) "$bundled_rule" >/dev/null; then
  echo "warning: assets/user-rule.md has drifted from token-efficiency.mdc;" >&2
  echo "         using the .mdc. Refresh with: $0 --print-rule > $bundled_rule" >&2
fi

warn_odd_home
primary=""
for home in "${homes[@]}"; do
  dest="$home/.cursor/skills/$skill_name"
  if [[ ! -d "$home" ]]; then
    echo "warning: skipping $dest (no such home directory)" >&2
    continue
  fi
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -R "$skill_dir" "$dest"
  echo "Skill installed: $dest"
  [[ -n "$primary" ]] || primary="$dest"
done

if [[ -z "$primary" ]]; then
  echo "error: could not install to any home directory" >&2
  exit 1
fi

for repo in "${repos[@]+"${repos[@]}"}"; do
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
  for tool in pbcopy clip.exe wl-copy "xclip -selection clipboard" "xsel --clipboard --input"; do
    cmd="${tool%% *}"
    command -v "$cmd" >/dev/null 2>&1 || continue
    if rule_text | $tool 2>/dev/null; then copied="$cmd"; break; fi
  done
fi

echo
if [[ -n "$copied" ]]; then
  echo "Rule text copied to your clipboard via $copied. One step left:"
  echo "  open Customize in the Cursor sidebar -> Rules -> paste -> save"
  echo "That scope applies to every repository on this machine."
else
  echo "Last step: paste the text below into Customize -> Rules in the Cursor sidebar,"
  echo "which applies to every repository on this machine."
  echo "(Reprint any time with: $primary/scripts/install-global.sh --print-rule)"
fi
echo
echo "Then quit Cursor completely, reopen it, and confirm '$skill_name' appears"
echo "under Customize -> Skills in a window with a DIFFERENT project open."
if [[ -z "$copied" ]]; then
  echo
  echo "----------------------------------------------------------------------"
  rule_text
fi
