# Methodology — competitor-gap-analysis

Load this only if you need to explain *how* a gap was computed or defend it.

## Inputs

The script consumes one `gap.json` the agent assembled from MCP output:

```json
{
  "me": <list_videos envelope or bare list>,
  "competitors": [
    {"name": "@handle", "videos": <list_creator_videos envelope or list>},
    ...
  ]
}
```

Each video is an `McpPostSummary`. Per video the script reads:

- `metrics.views` and `metrics.engagement_rate` (cohort medians).
- `duration` (seconds) and `title`/`caption` (sequel detection + keyword fallback).
- `content_themes` (the analysis themes) when `include_analysis=true` was passed.

`me` and each competitor's `videos` are unwrapped with `coerce_videos`, so the
raw tool envelope, a bare list, or a single video object all work.

## Theme extraction

Themes are the unit of comparison. Two sources, in priority order:

1. **Analysis themes** — each video's `content_themes` list (populated when the
   videos were pulled with `include_analysis=true`). Themes are lowercased and
   de-duplicated per video so one video can't inflate a theme's coverage.
2. **Keyword fallback** — if fewer than ~40% of all videos carry analysis
   themes, the script mines pseudo-themes from `title` + `caption`: lowercase,
   tokenize on non-alphanumerics, drop a built-in stopword set and tokens under
   3 characters, count term frequency across the whole corpus, and keep the most
   frequent terms as the candidate theme vocabulary. Each video is then tagged
   with whichever of those terms appear in its text.

The two modes never mix: it's analysis themes for everyone or keywords for
everyone, so coverage shares stay comparable across cohorts.

## Cohorts and coverage share

Three cohort views are computed:

- **you** — the `me` videos.
- **each competitor** — that competitor's videos (reported individually).
- **competitors (pooled)** — all competitors' videos concatenated.

For a theme `t` in a cohort, **coverage share** is the fraction of that cohort's
videos tagged with `t` (count of videos with `t` divided by cohort size). A
video tagged with three themes contributes to three themes' counts, so shares
across themes do not sum to 1 — they're per-theme prevalences, not a partition.

## Gaps

- **Content gap** — a theme where the *pooled competitor* coverage share is high
  (≥ 20% of competitor videos) **and** it appears for at least 2 distinct
  competitor videos (so a single post can't manufacture a gap), **and** your own
  coverage share is ~0 (no videos, or below a small floor). Gaps are ranked by
  competitor coverage share, then by the median views competitors get on that
  theme, so the biggest, highest-reach gaps surface first.
- **Owned territory** — a theme you cover on ≥ 2 of your videos where the pooled
  competitor coverage share is at/near zero. Ranked by your coverage share.

## Format comparison

A small Me vs. Competitors (pooled) table on four metrics, each a cohort median:

- **Median duration** (seconds).
- **Sequel / series rate** — share of videos whose title/caption matches a
  part/episode/numbered-series pattern (`part 2`, `ep 3`, `#4`, …).
- **Median engagement rate** — `metrics.engagement_rate`, or interactions ÷
  views when the field is absent.
- **Median views.**

Each row notes the direction of the gap (who is higher) so format differences
read at a glance. Medians, not means, because views and engagement are
heavy-tailed and a single viral post would distort a mean.

## Thresholds (defaults)

- Competitor coverage to flag a gap: **≥ 0.20** share **and ≥ 2** videos.
- Your coverage to *not* count as a gap: anything above a small floor
  (one stray video doesn't disqualify a real gap).
- Owned territory: **≥ 2** of your videos, competitor share **≤ ~0.05**.
- Minimum to run: **≥ 1 competitor** with **≥ 3 videos**.

## Caveats (state these to the user when relevant)

- **A gap is a lead, not a verdict.** It means a competitor is getting reach on a
  topic you're absent from. Whether it works for *your* audience is the A/B test.
- **Themes are approximate.** Analysis themes are model-derived; keyword
  fallback is coarser still. Read the named themes, not just the counts — a
  surprising gap is sometimes a labeling artifact.
- **Top-15 is a snapshot.** Pulling each cohort's top videos biases toward each
  account's hits; that's intentional (you want to compare bests), but it isn't
  the full catalog. Re-run as you ship against the gaps.
- **Small competitor sets are noisy.** One competitor with 4 videos gives thin
  coverage shares. More competitors and more videos sharpen every threshold.
