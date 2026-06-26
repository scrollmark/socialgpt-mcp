---
name: hook-retention-teardown
description: >-
  Tear down what a creator's best hooks do that their flops don't. Use when a
  SocialGPT user asks "why do my best videos pop and others flop", "what makes a
  good hook for me", "compare my top vs bottom posts", "what should my openings
  do", or wants a teardown of their own hooks and pacing. Pulls the user's top
  and bottom performers via the SocialGPT MCP, reads each one's transcript and
  hooks, then computes deterministic text/pacing metrics — words-per-second,
  time-to-hook, first-person vs instructional language, specificity, curiosity
  words, CTA usage, hook style — and writes a visual report showing the
  dimensions where winners and losers differ most. Requires the SocialGPT MCP
  server to be connected.
license: MIT
---

# Hook & Retention Teardown

Find the language and pacing patterns that separate a creator's **winners from
their flops** — so they learn what their own best hooks and openings do that
their weak ones don't. This is the deterministic, transcript-level complement to
qualitative hook advice: instead of vibes, you measure words-per-second,
opener style, first-person language, and CTA placement, then show exactly where
the top cohort diverges from the bottom.

This skill pairs with the **SocialGPT MCP server** (`https://mcp.gpt.social/mcp`).
The MCP provides the data; this skill provides the deterministic analysis and a
shareable report. If the SocialGPT tools below aren't available, the user needs
to connect the MCP first: https://gpt.social/integrations/mcp

## When to use

Trigger on requests like: *"why do my best videos pop and others flop?"*,
*"what makes a good hook for me?"*, *"compare my top and bottom posts"*, *"what
should my openings do?"*, *"do a teardown of my hooks"*, *"what do my winners do
differently?"*

## Workflow

1. **Confirm access.** Make sure the SocialGPT MCP tools are connected. If
   `list_videos` isn't available, point the user to the connect page above and
   stop.

2. **Find the winners and flops.** Call:
   ```
   list_videos(sort="top", limit=20)
   ```
   Rank by `metrics.views`. Take the **top ~5** and the **bottom ~5**. Exclude
   Instagram videos with `views == 0` (Instagram hides reel plays, so a 0 there
   isn't a real flop).

3. **Fetch each video's full analysis.** For every selected video, call:
   ```
   get_video_analysis(platform, post_id)
   ```
   This returns the transcript, hooks, and suggested hooks the teardown needs.
   - Right after ingest this may return `{"status": "pending"}` — that's not an
     error. **Wait ~20s and retry.** Only include a video once its analysis is
     ready (it has a `transcript`).
   - Skip any video that still has no transcript after retrying; it just won't
     count toward the teardown.

4. **Assemble the input file.** Collect the `get_video_analysis` results into one
   JSON file named `teardown.json` in the working directory, shaped:
   ```json
   {
     "top":    [ <get_video_analysis result>, <...> ],
     "bottom": [ <get_video_analysis result>, <...> ]
   }
   ```
   Put each analysis object verbatim — the script reads `post`, `transcript`,
   `transcript_segments`, `hooks`, and `suggested_hooks` itself.

5. **Run the analysis** (it has no third-party dependencies):
   ```
   python scripts/analyze.py teardown.json
   ```
   The script reads `teardown.json`, computes per-video metrics, compares the two
   cohorts, prints a Markdown summary to stdout, and writes
   `hook-retention-teardown.html`.

6. **Relay the result.** Present the Markdown summary the script printed, then
   offer the user the generated `hook-retention-teardown.html` to download / open
   (on Claude.ai it appears as a downloadable file).

## What the script does

For every video that has a transcript, it computes deterministic text/pacing
metrics, then aggregates each as a cohort median (numeric) or majority share
(categorical) for `top` vs `bottom` and surfaces the dimensions where they
differ most:

- **Pacing** — words per second (transcript word count ÷ duration) and an
  approximate time-to-first-hook (start of the first segment carrying a question,
  number, or strong opener).
- **Language** — first-person markers (I, my, we) vs instructional ones (you,
  your) as a ratio; specificity (density of numbers, %, $, proper nouns);
  curiosity/emotion words ("actually", "nobody", "secret", "why"…); and CTA
  presence + rough position (early / middle / late / absent).
- **Hook style** — the opening (first ~12 transcript words, or the top
  suggested/extracted hook) classified as question, bold-claim, story, listicle,
  or visual/other.

The report shows: callouts (videos analyzed, the biggest differentiator,
winners' median words/sec), a side-by-side table of winners vs flops per
dimension, a breakdown of hook styles among the winners, and three plain-English
patterns to copy. See `references/methodology.md` for the exact definitions.

## Notes

- **Needs a real comparison.** It requires at least 2 videos with transcripts in
  each cohort (or 3 total) and will tell you to fetch more / wait for pending
  analyses rather than invent findings.
- **Describes, not explains.** These are counts on the creator's own
  transcripts — they show *what differs* between winners and flops, not *why* it
  works. Treat each pattern as a lead to A/B test.
- **Re-runnable.** Suggest re-running as the account grows and the back catalog
  of winners and flops changes.
- **Part of a larger loop.** This is the hook-study stage of the
  [**going-viral**](../going-viral) strategy loop — pair it with the audit and
  gap skills for the full research-to-review cycle.
