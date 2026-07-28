# Auditing where the context went

## Read the breakdown, don't guess

The context ring beside the prompt input shows how full the window is. Clicking it
opens a breakdown tray that splits total tokens by category:

| Category | What it is | If it is large |
| --- | --- | --- |
| Conversation | Live messages and tool results | The usual culprit. Something big was read, or the thread has run long. |
| Summarized conversation | Older turns Cursor compressed automatically | The thread already outgrew the window. Finish and start fresh. |
| Tools | Tool definitions | Mostly fixed. |
| Rules | Rule files pulled in | An always-apply rule is too long, or too many rules match. |
| Skills | Skill descriptions injected into system context | Descriptions only; bodies load on demand. Trim descriptions if bloated. |
| MCP | MCP server tool definitions | Disable MCP servers you are not using in this thread. |
| Subagents | Subagent definitions | Mostly fixed. |

Cursor compresses older turns into a summary automatically as the window fills. That
keeps the thread alive but does not make it cheap: the summary is still re-sent every
turn, and detail has been lost. Treat a large "summarized conversation" segment as a
signal that the thread should have ended earlier.

Per-thread tokens are separate from spend. Dollar amounts and the input / output /
cache-write / cache-read counters live on the spending dashboard; interpret those with
`cost-model.md`.

## Post-mortem questions for an expensive thread

1. **What was the largest single thing read?** One large data file, lock file, or full
   test log early in a thread accounts for more than dozens of small reads late in it.
2. **How many turns did it take, and how many were one command each?** Sequential
   single-command turns are the most common avoidable cost; independent calls batch
   into one turn.
3. **Was anything read twice?** Re-reading a file that had not changed pays twice for
   content that was already resident.
4. **Did unrelated tasks share the thread?** Every turn of task three paid for tasks
   one and two.
5. **Did exploration happen in the main thread?** Reconnaissance belongs in an
   `explore` subagent or a side chat, where the reading is discarded afterward.
6. **Were there idle gaps or a mid-thread model switch?** Both invalidate the prefix
   cache and re-bill the whole history at full input price.

## In-thread remedies

- `/summarize` (alias `/compress`) compacts the current conversation on demand in the
  CLI. Useful when a thread must continue but its history has grown unwieldy.
- `/clear` (aliases `/new`, `/new-chat`) starts a fresh session — the cheapest fix
  when the current task is done.
- Side chats keep exploratory questions out of the main transcript: the parent history
  is passed as hidden reference context and the digression does not accumulate in the
  main thread.
- `/rewind` and `/fork` help abandon a bad path instead of arguing with it across more
  turns, though both invalidate cache from the branch point onward.

## Structural remedies

- Add bulk paths to `.cursorignore`, which excludes them from agent reads, codebase
  search, and `@` mentions. Confirm nothing needed is caught by the pattern first.
- Keep always-apply rules to tens of lines; move detail into skill reference files that
  load only when relevant.
- Scope rules with `globs` and skills with `paths` so they stay out of context for
  unrelated work.
- Turn off MCP servers that are not needed for the current work; their tool definitions
  sit in context for the whole thread.
