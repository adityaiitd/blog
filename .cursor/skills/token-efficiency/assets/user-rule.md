# Token discipline

Every assistant turn re-sends the whole conversation as cached input, so cost scales
with `turns x context size`, not with the length of your answers. A short reply in a
long thread is expensive; a long reply in a short thread is cheap. Optimize for fewer
turns and a smaller resident context.

## Never trade these away

Correctness outranks token savings. Specifically:

- Read a file before editing it, and read enough of it to be correct.
- Verify claims about the code instead of guessing to avoid a read.
- Run the tests or checks that a change actually warrants.
- If saving tokens would risk a wrong answer, spend the tokens and say why.

## Spend fewer turns

- Put independent tool calls in a single message instead of one per turn.
- Chain dependent shell commands with `&&` in one call.
- Decide the full set of files to read before reading any of them, rather than
  discovering them one turn at a time.
- Do not re-verify something already established earlier in the thread.

## Keep the resident context small

Anything read into context is re-billed on every later turn, so what you read costs
far more than once.

- Locate code with Grep (`output_mode: files_with_matches`, or `head_limit`) before
  reading files.
- For files over ~500 lines, read the relevant range with `offset`/`limit`. Read a
  whole file when you genuinely need the whole file.
- Never read bulk or generated content into context: lock files, build output,
  minified bundles, large CSV/JSON/XLSX data, full test or CI logs. Characterize
  them from the shell instead (`wc -l`, `head -5`, `rg -c`, `jq` on a slice,
  `cut -c1-400`). A 12 MB data file is roughly 3M tokens.
- Send noisy command output to a file and read only the part that matters:
  `cmd > /tmp/out.log 2>&1; tail -40 /tmp/out.log`.
- Scope test runs to the affected path before running a full suite.
- Do not re-read a file already in context; scroll back. Re-read only after it changed.

## Delegate bulk exploration

- Use the `explore` subagent for open-ended questions ("where is X handled", "how does
  Y flow"). Its reading stays in its own context window and only the answer returns here.
- Ask a subagent for findings (paths, line numbers, the mechanism) rather than pasted code.
- Do not fan out parallel subagents on a question one Grep answers; N subagents cost
  roughly N times one agent.

## Bound the thread

- State plainly when a task is finished, and recommend a fresh chat for the next
  unrelated task. A long thread pays for its entire history on every turn.
- Do not restate prior work, re-summarize the plan, or repeat file contents already shown.
