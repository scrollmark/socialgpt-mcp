---
name: going-viral
description: >-
  The viral-content operating loop — research what's already winning, find what
  actually drives a creator's own hits, ideate against the data, ship one
  experiment at a time, review, repeat. Use when a SocialGPT user asks "how do I
  go viral", "why isn't my content taking off", "give me a content strategy",
  "what should I post next", "how do I grow / get more views / get more reach",
  or wants a repeatable system instead of post-and-pray. Grounds every step in
  the user's real data via the SocialGPT MCP and routes into the
  content-performance-audit, competitor-gap-analysis, and hook-retention-teardown
  skills for the deep dives. Works without a connection (it still teaches the
  playbook), but is far stronger with the SocialGPT MCP connected.
license: MIT
---

# Going Viral

Virality is closer to a science than a lottery. The creators who hit
consistently aren't luckier — they run a **loop**: study what already works, form
a hypothesis about *why*, test it with one post, and feed the result back in.
This skill is that loop, and it's the **conductor** for the rest of the SocialGPT
toolkit — it grounds each stage in your real data and hands the heavy analysis to
the specialist skills.

This skill pairs with the **SocialGPT MCP server** (`https://mcp.gpt.social/mcp`).
The MCP provides your data; this skill provides the strategy that turns that data
into your next post. The other skills below ship the deterministic analysis.

> **Better with a connection.** If the SocialGPT tools aren't available, this
> skill still works — it teaches the full playbook. But it's far stronger
> connected: instead of generic advice it studies *your* real outliers, *your*
> drivers, and *your* hooks. If you haven't connected an account yet, do it here
> first: https://gpt.social/integrations/mcp (public/competitor analysis works
> with no account; your own data needs a connected account).

## When to use

Trigger on the broad, upstream strategy asks: *"how do I go viral?"*, *"why isn't
my content taking off?"*, *"give me a content strategy"*, *"what should I post
next?"*, *"how do I grow my account / get more reach?"*, *"build me a repeatable
system"*, *"I'm posting a lot and nothing's working."*

These sit *above* the three specialist skills — when the user wants the whole
system, start here and route into them. When they ask a narrow question ("what
drives my views", "compare me to @rival", "teardown my hooks"), go straight to
the matching specialist.

## The loop

Five stages. At each one, pull the user's real data with the MCP, apply the
referenced playbook file, and hand the deterministic analysis to the specialist
skill.

| Stage | What you do | Pull via the MCP | Hand off to |
|-------|-------------|------------------|-------------|
| **1. Research outliers** | Find creators/formats that go viral *repeatedly* in or adjacent to the niche; study why. | `list_creator_videos(sort="top")`, `get_creator`, `list_similar_videos`, `search_videos`; `analyze_creator` + `get_analysis_status` for creators not yet in the library | **competitor-gap-analysis** |
| **2. Find your own drivers** | Isolate what actually predicts *this* account's views — length, timing, platform, format. | `list_videos(sort="top")`, `get_content_profile`, `get_account_metrics` | **content-performance-audit** |
| **3. Study winning hooks & formats** | Read what the top posts' openings and pacing do that the flops don't. | `get_video_analysis` (transcript, hooks, scenes) | **hook-retention-teardown** |
| **4. Ideate against the data** | Generate many ideas grounded in stages 1–3, then rank and cut hard. | `get_content_profile` (pillars + voice) + the outputs above | — (reason it out; see references) |
| **5. Ship one + review** | Make and ship **one** post — one clean hypothesis test — then read the result and update what you believe. | `get_post_metrics_history`, `get_growth_summary`, `get_account_metrics` | re-run audit / teardown |

The discipline that makes the loop work: **one experiment at a time** (not a
batched calendar), every belief held as a **hypothesis** until a Gold-vs-Bronze
comparison survives it, and a flop **diagnosed by stage** (bad research vs bad
execution) rather than blamed on the idea or the algorithm. See
[viral-content-model](./references/viral-content-model.md) for the full loop and
[self-analysis-and-iteration](./references/self-analysis-and-iteration.md) for
reading a result.

## How to go deeper

The `references/` folder is the knowledge base — 18 focused playbook files. Load
the one that fits the stage you're in rather than reading them all up front:

- **The loop & mindset** — [viral-content-model](./references/viral-content-model.md),
  [viral-mindset-and-myths](./references/viral-mindset-and-myths.md),
  [generalist-principle](./references/generalist-principle.md)
- **Research & analysis** — [reverse-engineering-outliers](./references/reverse-engineering-outliers.md),
  [viral-performance-drivers](./references/viral-performance-drivers.md),
  [self-analysis-and-iteration](./references/self-analysis-and-iteration.md)
- **Formats** — [proven-viral-formats](./references/proven-viral-formats.md),
  [viral-format-engineering](./references/viral-format-engineering.md)
- **Ideation** — [content-ideation-pipeline](./references/content-ideation-pipeline.md)
- **Hooks & retention** — [hook-anatomy](./references/hook-anatomy.md),
  [hook-iteration](./references/hook-iteration.md),
  [narrative-tension-and-retention](./references/narrative-tension-and-retention.md),
  [story-structure-short-form](./references/story-structure-short-form.md)
- **Algorithm & distribution** — [platform-algorithm-fluency](./references/platform-algorithm-fluency.md),
  [algorithm-seeding-and-trust](./references/algorithm-seeding-and-trust.md),
  [early-engagement-diagnostics](./references/early-engagement-diagnostics.md),
  [communication-algorithm-triple-f](./references/communication-algorithm-triple-f.md)
- **Execution** — [execution-craft-and-nuance](./references/execution-craft-and-nuance.md)

## Notes

- **This skill conducts; it doesn't compute.** The hard numbers — significance
  tests, gap matrices, hook metrics — come from the three specialist skills. Run
  them at the stages above and feed their findings back into the loop.
- **One post, one hypothesis.** Resist batching a month of content. You learn
  nothing between underperformers; you learn everything from one post analyzed
  deeply.
- **Leads, not verdicts.** Everything the data surfaces is the best thing to
  *test next*, not a guarantee. Hold it loosely and let the next result update it.
- **Re-runnable.** The loop never ends — re-research and re-audit as the account
  grows and what works shifts.
