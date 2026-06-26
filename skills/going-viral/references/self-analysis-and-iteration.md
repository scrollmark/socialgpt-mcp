---
name: self-analysis-and-iteration
description: How to diagnose your own posts with ratios over raw reach — read view rate and the retention curve to find exactly where viewers drop, then benchmark against a top reference and iterate.
---

# Self-Analysis & Iteration

The last stage of the loop (see [viral-content-model](./viral-content-model.md)): after a post, figure out *why* it did what it did and feed that into the next one. The trap is reading the wrong numbers and copying the wrong lessons. Pairs with [early-engagement-diagnostics](./early-engagement-diagnostics.md) (the first-hours read) and [reverse-engineering-outliers](./reverse-engineering-outliers.md) (the comparison method).

## Ratios over absolutes

Reach and impressions look impressive but only mean the content *appeared* — not that anyone watched. Judge by ratios:
- **View rate** — share of reach that watched past ~3 seconds. A low view rate is a diagnosis: your opening is weak. Fix the first seconds, not the whole video.
- **Retention curve** — the % still watching across the duration, starting at 100% and tapering. The *dips* tell you exactly where interest drops — go fix those specific segments. A mid-video uptick means your real hook is buried there; move it forward.

For the user's own **Instagram Reels** and **YouTube Shorts**, pull the real figures with `get_post_retention` (average watch time, view %, and for YouTube the retention curve with the biggest drop-off already located) instead of reasoning in the abstract. TikTok exposes no watch-time data.

Metrics and their names differ per platform — learn your native analytics dashboard rather than trusting a generic chart.

## Benchmark against a Gold reference

Don't grade in a vacuum. Open your finished video side by side with the top-performing reference it was modeled on, and compare on *presentation* — pacing, transitions, audio, structure, the drivers you intended — not on topic. Where the reference outshines you, that's your edit list. Iterate until yours produces the same impact.

## Make your best post the new benchmark

Analyze your *wins*, not just your misses. Your top performer becomes the reference for what's next. Diagnose precisely why it worked — small fixes (often the first few seconds) can move a video from good to breakout. Without analysis you risk reusing the part that actually underperformed.

## One iteration at a time

Ship one post, read it, adjust, ship the next. Single-iteration testing keeps each post a clean hypothesis. Don't batch — you lose the ability to attribute cause (see [viral-content-model](./viral-content-model.md)).

## Quality over frequency

Prefer fewer breakthrough posts to many bland ones. Deep analysis may mean posting *less*. Before publishing, gut-check your confidence it'll stand out; if you're not convinced, hold and sharpen it. Bland content erodes both viewer trust and the algorithm's willingness to promote you (see [algorithm-seeding-and-trust](./algorithm-seeding-and-trust.md)).

## What NOT to do

- Don't celebrate reach/impressions; they don't prove anyone watched.
- Don't fix "the whole video" when a low view rate points at the first 3 seconds, or when the retention curve points at one segment.
- Don't post on autopilot because it's a certain weekday.
- Don't skip analyzing your hits — you'll copy the wrong thing next time.
