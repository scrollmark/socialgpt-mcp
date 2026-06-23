# Methodology — hook-retention-teardown

Load this only if you need to explain *how* a metric was computed or defend a
finding.

## Inputs

The script consumes the full `McpPostAnalysis` objects returned by the SocialGPT
MCP `get_video_analysis` tool, grouped by the agent into a single file:

```json
{ "top": [ <get_video_analysis result>, ... ],
  "bottom": [ <get_video_analysis result>, ... ] }
```

Per video it reads:

- `post` — for `metrics.views`, `duration` (seconds), `platform`, `title`.
- `transcript` (preferred) or `transcript_segments[].text` (joined) — the text
  every language/pacing metric is computed on.
- `transcript_segments[].start` — for the time-to-first-hook estimate.
- `suggested_hooks[0]` / `hooks[0]` — used only as a fallback opener when the
  transcript is missing words.

A video is **skipped** (not counted) if it has no usable transcript — including
analyses still returning `{"status": "pending"}`.

## Per-video metrics (all deterministic, stdlib only)

**Pacing**
- *Words per second* = transcript word count ÷ video duration (seconds). Words
  are `[A-Za-z']+` tokens. Skipped when duration is missing/zero.
- *Time to first hook* ≈ the `start` (seconds) of the first transcript segment
  that contains a question mark, a number, a question-word, or a story opener. If
  there is no segment timing, the open itself is treated as the hook (0s).

**Language**
- *First-person : instructional ratio* = count of first-person markers (`i`,
  `my`, `we`, `me`, `our`, …) ÷ count of instructional markers (`you`, `your`,
  `you're`, …). `>1` means the creator talks about themselves more than they
  lecture.
- *Specificity* = (count of numbers / `%` / `$` + count of non-sentence-initial
  Capitalized tokens) ÷ word count. A per-word density of concrete detail.
- *Curiosity-word density* = count of built-in curiosity/emotion words
  ("actually", "honestly", "surprisingly", "nobody", "secret", "truth",
  "mistake", "never", "always", "stop", "why", …) ÷ word count.
- *CTA usage & position* = scans for CTA phrases ("follow", "comment", "link",
  "save this", "share", "subscribe", …). Position is the first match's relative
  offset in the transcript: early (<⅓), middle (⅓–⅔), late (>⅔), or absent.

**Hook style** — the opening (first ~12 transcript words, or the top
suggested/extracted hook if the transcript has no words) is classified into one
of: `question` (contains `?` or starts with a question word), `listicle` (starts
with a list cue or contains a number), `story` (starts with `I`/`when`/`my`/…),
`bold-claim` (starts with an absolute/superlative cue), or `visual/other`.

## Cohort comparison

Each numeric metric is aggregated as the **median** of the cohort (robust to one
weird video). Each categorical metric (`hook_style`) is summarized by its
**majority value and share**; CTA usage is the **share of the cohort that has
any CTA**.

The **biggest differentiator** is the dimension with the largest gap between
cohorts. For numeric dimensions the gap is the relative difference
`|top − bottom| ÷ max(|top|, |bottom|)`; for `hook_style` the gap is `1` when the
dominant style differs between cohorts and `0` when it matches; for CTA usage it
is the absolute difference in shares.

## Degrade-gracefully threshold

The teardown needs a real comparison: **≥2 videos with transcripts in each
cohort, or ≥3 total**. Below that it exits with a helpful message (and flags how
many supplied videos had no transcript yet, i.e. likely still pending) instead of
reporting noise.

## Caveats (state these to the user when relevant)

- **Descriptive, not causal.** These are counts on the creator's own
  transcripts. They tell you *what differs* between winners and flops, not *why*
  one worked — the real cause may be visual, topical, or timing-based and
  invisible to text metrics.
- **Small samples wobble.** With ~5 per cohort, one outlier shifts a median.
  Prefer differences that persist across re-runs as the catalog grows.
- **Transcript quality varies.** ASR errors, music-only segments, and missing
  captions all reduce signal; the metrics are best-effort on whatever text the
  analysis pipeline produced.
