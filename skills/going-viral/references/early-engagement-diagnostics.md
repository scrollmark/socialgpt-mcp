---
name: early-engagement-diagnostics
description: How to read hour-1, hour-6, and day-1 metrics on a fresh post — what early signals predict, when to declare a flop, when to wait it out.
---

# Early Engagement Diagnostics

## What hour 1 actually tells you

Hour 1 is mostly *delivery*, not performance. The platform is testing the post on a small seed audience (~5–10% of typical reach for established accounts).

**Strong signal**: completion/watch-time rate above your baseline.
**Weak signal**: raw view count — it's mostly platform-controlled at this stage.

Don't compare hour 1 likes to your average — your average is hour 24+. A post pulling 5% of its eventual likes in hour 1 is on a normal trajectory.

## What hour 6 actually tells you

Hour 6 is when the algorithm has decided whether to expand. Look at:

- **View velocity** (views over time delta) vs your typical posts at the same age
- **Save rate** (saves / views) — saves are the strongest "show this to more people" signal on Reels and TikTok
- **Comment rate** (comments / views) — but only weight thoughtful comments; "🔥🔥" doesn't help

If hour 6 view velocity is below your 30-day median for that hour, the post is unlikely to recover. Algorithm decisions here are mostly sticky.

## What day 1 actually tells you

Day 1 reveals reach ceiling. Compare to your trailing 30-day median:

| Day-1 vs median | Verdict |
|---|---|
| <50% | Flop — kill follow-up content, don't repost |
| 50–100% | Mid — fine, not worth iterating on |
| 100–150% | Above average — note the hook + topic |
| 150%+ | Spike — double down: same topic, different angle, within 48h |

## When to wait

- **Niche/educational posts**: can ramp slowly via search and "for you" recirculation. Give them 72h before declaring.
- **Sound-driven trend posts**: hour 6 verdict holds. Trends decay faster than the algorithm can rescue.
- **Carousels (IG)**: slower burn than Reels. Day 3 is the real read.

## Counter-intuitive cases

- **Lots of likes, no saves**: the post is entertaining but disposable. Won't drive follower growth.
- **Few likes, high saves**: useful content. Will keep accumulating reach for weeks.
- **High shares, low saves**: viral but won't convert to followers. Don't read it as "now I post this style every day."
- **Comments full of questions**: confused audience. Hook is unclear or scope is too broad.
- **Comments full of "same"/"this is me"**: identification — strongest follow-conversion signal.

## Read ratios, not raw reach

Reach and impressions only mean the post was *shown*. Judge the early read on ratios: **view rate** (share of reach watching past ~3s) diagnoses the opening — a low view rate means fix the first seconds, not the whole post — and the **retention curve**'s dips show exactly where viewers leave; for the user's own IG Reels and YT Shorts you can pull the actual figures with `get_post_retention`. For the full post-mortem and benchmarking against a top reference, see [self-analysis-and-iteration](./self-analysis-and-iteration.md).

## What NOT to do at hour 1

- Don't delete a "flopping" post in hour 1. The signal isn't there yet.
- Don't reply to every comment in the first hour expecting it to boost reach. It's a myth — replies help engagement metrics on the *comment*, not the post.
- Don't change the caption mid-stream. It resets some platforms' indexing.
