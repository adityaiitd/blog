# The cost model, worked from a real bill

## The four token counters

| Counter | What it means | Relative price |
| --- | --- | --- |
| Input | Fresh prompt tokens, not served from cache | Baseline (1x) |
| Cache write | Prompt tokens stored into the prefix cache the first time | ~1.25x input |
| Cache read | Prompt tokens served from the prefix cache | ~0.1x input |
| Output | Tokens the model generates | ~5x input |

Cache reads are individually the cheapest, which is exactly why they are easy to
ignore and usually end up being the whole bill: they are the only counter that grows
with the *square* of thread length.

## Worked example

Reported usage for one long agent thread:

```
claude-opus-5-thinking-high (2 calls), $46.65
  input        226
  output        70,146
  cache write  761,972
  cache read   80,274,496
```

Cache reads are 80,274,496 of 81,106,840 billed tokens, or **99.0%**. The dollar split
follows: at a rate card of $5/M input, $6.25/M cache write, $0.50/M cache read and
$25/M output — which reproduces the reported total to the cent — the breakdown is

| Counter | Tokens | Cost | Share |
| --- | --- | --- | --- |
| Cache read | 80,274,496 | $40.14 | 86.0% |
| Cache write | 761,972 | $4.76 | 10.2% |
| Output | 70,146 | $1.75 | 3.8% |
| Input | 226 | ~$0.00 | 0.0% |

The conclusion does not actually depend on that rate card. Cache reads outnumber output
tokens 1,144 to 1; no plausible discount makes output the problem.

### The re-read multiplier

Cache-write tokens approximate the *unique* content of the thread — each new chunk of
prompt is written to cache once. Cache-read tokens are what you paid to look at that
content again on later turns. Their ratio is the single most diagnostic number:

```
80,274,496 / 761,972 = 105x
```

Roughly 762k tokens of unique conversation were paid for about **105 times over**.
Every file read, tool result, and log line in that thread was re-billed on average 105
times. A healthy multiplier for a focused task is single digits to low tens.

### Reconstructing the shape of the thread

Two equations, assuming context grew at a roughly steady rate `g` per turn over `N`
turns:

```
unique content:  g x N          ~ 762k
cache reads:     g x N^2 / 2    ~ 80.3M
```

Solving gives `N ~ 210` turns and `g ~ 3.6k` tokens added per turn, so the average
resident context was about 80.3M / 210 = **380k tokens**, ending near 760k. Average
output per turn was 70,146 / 210 = **334 tokens**.

That is the diagnosis in one line: a few hundred short tool-call turns, each one
re-reading a context roughly four times larger than it needed to be.

### The quadratic consequence

Because cache reads go as `N^2`, thread length is superlinear in cost:

- Half the turns, same growth rate: **~4x cheaper**.
- Same turns, half the context growth: **~2x cheaper**.
- Both: **~8x cheaper**.

Splitting one 210-turn thread into three 70-turn threads costs about a third as much,
for the same work, because each thread's history restarts. This is why "finish the task,
then start a new chat" is a cost control and not just tidiness.

## The second bill: cache misses

```
gpt-5.6-sol-medium (1 call), $34.18
  input        1,474,193
  output          75,038
  cache write     26,468
  cache read   21,456,646
```

Here the re-read multiplier against total fresh content is 21.46M / 1.50M = **14.3x**,
much healthier. The anomaly is elsewhere: **1,474,193 fresh input tokens against only
26,468 cache writes.** Fresh input costs roughly ten times a cache read, so despite
being 6.4% of the tokens it is a large fraction of the cost — in full-price-equivalent
terms, 1.47M + 2.15M = 3.62M, of which fresh input is about 41%.

Large fresh-input counts mean the prefix cache kept missing. The usual causes:

- **Idle gaps.** Prefix caches expire in minutes. Coming back to a thread after a
  break re-sends the entire history at full input price.
- **Switching models mid-thread.** Each model keeps its own cache; the first turn after
  a switch pays full price for the whole history.
- **Editing or rewinding an earlier message.** Everything after the edit point is
  invalidated and re-cached.

Practical implication: work a thread in continuous bursts, avoid mid-thread model
switches on long threads, and prefer a fresh, small thread over resuming a stale
large one.

## Estimating before you spend

For a planned task, `cache reads ~ turns x average context`. Sanity-check a plan
against that before starting: 50 turns at a 60k average context is 3M cache reads;
the same 50 turns at a 400k average context is 20M. The work is identical. The
difference is entirely what you allowed into context and how long you kept it there.
