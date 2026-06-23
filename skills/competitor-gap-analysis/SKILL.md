---
name: competitor-gap-analysis
description: >-
  Compare a creator's top content against 1-3 named competitors to find where
  the competitors win and the creator is silent. Use when a SocialGPT user asks
  "what are my competitors doing that I'm not", "find my content gaps", "what
  should I steal from @rival", "where am I getting beaten", or wants a side-by-side
  read of their catalog vs. a competitor's. Pulls the user's top videos and each
  competitor's top videos via the SocialGPT MCP, extracts themes (from analysis
  or caption keywords), and writes a visual report of content gaps, owned
  territory, format gaps, and three angles to test. Requires the SocialGPT MCP
  server to be connected.
license: MIT
---

# Competitor Gap Analysis

Put a creator's best content next to 1-3 competitors' best content and answer
"**what are they winning on that I'm not even showing up for?**" — instead of
scrolling rivals' feeds and guessing, you measure the overlap.

This skill pairs with the **SocialGPT MCP server** (`https://mcp.gpt.social/mcp`).
The MCP provides the data; this skill provides the gap analysis and a shareable
report. If the SocialGPT tools below aren't available, the user needs to connect
the MCP first: https://gpt.social/integrations/mcp

## When to use

Trigger on requests like: *"what are my competitors doing that I'm not?"*,
*"find my content gaps"*, *"compare me to @rival"*, *"what should I steal from
them?"*, *"where am I getting beaten?"*, *"what topics do they own?"*

## Workflow

1. **Confirm access.** Make sure the SocialGPT MCP tools are connected. If
   `list_videos` and `list_creator_videos` aren't available, point the user to
   the connect page above and stop.

2. **Pull your own top content.** Call the MCP tool:
   ```
   list_videos(sort="top", limit=15, include_analysis=true)
   ```
   `include_analysis=true` is what gives each video its `content_themes` — the
   script extracts gaps far more accurately when themes are present (it falls
   back to caption keywords if they're missing).

3. **Pull each competitor's top content.** For each of the 1-3 competitors the
   user named, call:
   ```
   list_creator_videos(platform="<tiktok|instagram|youtube>", username="<handle>", sort="top", limit=15, include_analysis=true)
   ```
   If a competitor isn't in the library yet, run `analyze_creator(platform,
   username)` first, poll `get_analysis_status(job_id)` until done, then call
   `list_creator_videos`.

4. **Assemble `gap.json`.** Write a single JSON file in the working directory
   shaped like this (the raw tool envelopes are fine — the script unwraps them):
   ```json
   {
     "me": <the list_videos result, envelope or bare list>,
     "competitors": [
       {"name": "@rival_one", "videos": <that creator's list_creator_videos result>},
       {"name": "@rival_two", "videos": <...>}
     ]
   }
   ```

5. **Run the analysis** (it has no third-party dependencies):
   ```
   python scripts/analyze.py gap.json
   ```
   The script reads `gap.json`, builds the gap matrix, prints a Markdown summary
   to stdout, and writes `competitor-gap-report.html`.

6. **Relay the result.** Present the Markdown summary the script printed, then
   offer the user the generated `competitor-gap-report.html` to download / open
   (on Claude.ai it appears as a downloadable file).

## What the script does

It splits the videos into cohorts — **you**, each named competitor, and a pooled
**competitors** set — and for each cohort reads a theme distribution plus median
views, engagement rate, duration, and sequel/series rate.

- **Themes** come from each video's analysis `content_themes`. If themes are
  largely missing (e.g. `include_analysis` was false), it falls back to keyword
  topics mined from titles and captions (lowercased, tokenized, stopwords
  dropped, top terms treated as pseudo-themes).
- **Content gaps** — themes competitors cover heavily (≥20% of their videos, and
  ≥2 competitor videos) where you have ~zero coverage.
- **Owned territory** — themes you cover (≥2 of your videos) that competitors
  barely touch.
- **Format gaps** — a Me vs. Competitors (pooled) table on median duration,
  sequel rate, median engagement, and median views, with the direction of each
  gap called out.
- **Three content angles to test**, grounded in the biggest gaps.

See `references/methodology.md` for how themes, coverage shares, and gaps are
computed, plus the caveats.

## Notes

- **Needs a real competitor set.** It requires at least one competitor with ≥3
  videos. With fewer it tells you what to pull rather than inventing gaps.
- **Themes beat keywords.** Always prefer `include_analysis=true`. Keyword
  fallback finds topic words, but analysis themes are cleaner and the gaps are
  sharper.
- **Gaps are leads, not verdicts.** A gap means a competitor is getting reach on
  a topic you're absent from — it's the best thing to test next, not proof it'll
  work for your audience. The report says this explicitly.
- **Re-runnable.** Suggest re-running as you ship against the gaps; the owned/gap
  split shifts as both catalogs grow.
