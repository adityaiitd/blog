---
name: token-efficiency
description: Diagnose and reduce agent token/context spend - explain a high Cursor bill, audit where context went, budget a large multi-file task so it stays cheap, and choose read/search/subagent strategies that keep the resident context small. Use when someone asks why their usage or cost is high, mentions cache read or cache write tokens, hits or nears the context window limit, asks to make the agent cheaper or more efficient, or is about to start a long exploration across many or very large files.
---

# Token efficiency

The always-on habits live in `.cursor/rules/token-efficiency.mdc` and apply to every
request. This skill is the deeper material: the cost model, how to audit a bill, and
how to budget a task that is large enough to need a plan.

## The one fact that explains almost every large bill

Cached input dominates. Each assistant turn re-sends the entire conversation prefix,
so a thread's cost is approximately:

```
cost ~ (number of turns) x (average context size)
```

Output tokens are usually a rounding error. In the reference bill analyzed in
`references/cost-model.md`, cache reads were 99% of billed tokens and about 86% of the
dollar amount, while output was 4%. That has a blunt implication: **a file read early
in a long thread is paid for on every subsequent turn.** A 5k-token file read at turn
10 of a 300-turn thread costs roughly 1.5M tokens, not 5k.

The two levers are therefore turn count and resident context size. Nothing else moves
the number much.

## Budgeting a task before starting it

For anything spanning more than a few files, spend one turn planning the reads:

1. **Map before reading.** Use Grep to find the relevant files and line numbers. A
   `files_with_matches` search costs a few hundred tokens; reading six candidate files
   to find the right one costs tens of thousands, permanently.
2. **Decide what must be resident.** Files you will edit need to be in context. Files
   you only need to understand can be summarized by a subagent instead.
3. **Delegate the survey.** Open-ended reconnaissance goes to the `explore` subagent,
   which reads in its own context window and returns only conclusions.
4. **Sequence edits so verification is cheap.** Group changes to one file into one
   edit pass; run the narrowest check that proves the change, and save the full suite
   for the end.
5. **Stop at task boundaries.** When the task is done, say so and recommend a new chat.
   Carrying a finished task's context into the next one taxes every future turn.

## Choosing how to look at something

| Situation | Do this | Not this |
| --- | --- | --- |
| Finding where a symbol lives | Grep with `files_with_matches` | Reading candidate files |
| Understanding an unfamiliar subsystem | `explore` subagent, ask for paths and mechanism | Reading the directory yourself |
| A file over ~500 lines | Grep for the anchor, then read with `offset`/`limit` | Whole-file read |
| A file you are about to edit | Read it properly, in full if needed | Guessing from a grep hit |
| Data files, fixtures, lock files, bundles | Shell summaries: `wc -l`, `head -5`, `rg -c`, `jq`, `cut -c1-400` | Any read into context |
| Build, test, or CI output | Redirect to a file, then `tail -40` | Letting the full log land in context |
| Something already read this thread | Scroll back | Re-reading it |
| Something changed since you read it | Re-read the changed part | Assuming your stale copy is current |

## Working with subagents

Subagents are the only way to look at a lot of material without paying for it forever,
because their context is discarded when they return. Use them for reconnaissance, not
for work you will need to re-derive.

- Give a subagent a self-contained brief; it cannot see this conversation.
- Ask for specific outputs: file paths, line numbers, the control flow, the answer.
  Explicitly tell it not to paste large code blocks back.
- One subagent per genuinely independent question. Parallel fan-out multiplies cost,
  so it only pays off when the questions are truly separate and each is substantial.
- Do not delegate what a single Grep answers.

## Repo hygiene that lowers the floor

- `.cursorignore` keeps paths out of agent reads, codebase search, and `@` mentions.
  Good candidates: large data files, build output, vendored dependencies, fixtures.
  Verify nothing needed for the work is excluded before adding entries.
- Keep always-apply rules short. They are re-sent on every request, so an always-on
  rule should be tens of lines, with detail moved into skill reference files that load
  only when relevant.
- Scope narrower rules with `globs` and skills with `paths` so they stay out of context
  for unrelated work.

## Making this apply everywhere

The two halves have different available scopes:

| Scope | Covers | How |
| --- | --- | --- |
| `~/.cursor/skills/` | This skill, every project on the machine | `scripts/install-global.sh` |
| `.cursor/rules/*.mdc` with `alwaysApply: true` | One repository, shared with collaborators | Commit the rule; `install-global.sh --repo PATH` adds it elsewhere |
| User Rules | Every repository on one machine | Paste once into Customize -> Rules in the sidebar. Not file-based, so it cannot be scripted; the installer puts the text on your clipboard. |
| Team Rules | Every repository for a whole team | Cursor dashboard, team admins on Team/Enterprise plans. Plain text with no frontmatter; a Team Rule with no glob applies to every conversation. |

Installer usage:

```bash
scripts/install-global.sh                        # skill -> ~/.cursor/skills, rule -> clipboard
scripts/install-global.sh --repo ~/code/app      # also drop the .mdc into another repo
scripts/install-global.sh --print-rule           # just print the User Rules text
```

Skills are discovered when Cursor starts, so restart after installing one and confirm it
appears under Customize -> Skills. Rule precedence is Team Rules, then Project Rules,
then User Rules, all merged. Note that skills are model-invoked and have no always-apply
flag, which is why the always-on habits live in the rule and only the deeper material
lives here.

## Detailed references

- `references/cost-model.md` - the arithmetic behind a real bill, how to read
  input/output/cache-write/cache-read numbers, and how to estimate a thread's cost.
- `references/auditing-a-thread.md` - how to find what is consuming a context window
  and what to change next time.
- `assets/user-rule.md` - the rule body without frontmatter, ready to paste into User
  Rules. Kept in sync with `.cursor/rules/token-efficiency.mdc`; the installer warns on
  drift and can regenerate it with `--print-rule`.
