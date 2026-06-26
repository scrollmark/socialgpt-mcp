---
name: content-performance-audit
description: >-
  Statistically audit what actually drives a creator's views. Use when a
  SocialGPT user asks "what drives my views", "why do some of my posts pop",
  "what should I double down on", or wants a data-backed performance review of
  their own content. Pulls the user's videos via the SocialGPT MCP, then runs
  real significance tests (Pearson, Kruskal-Wallis) to rank the factors —
  length, timing, platform, format — that predict view count, and writes a
  visual report. Requires the SocialGPT MCP server to be connected.
license: MIT
---

# Content Performance Audit

Turn a creator's own post history into a ranked, statistically-tested answer to
"**what actually drives my views?**" — instead of guessing, you measure.

This skill pairs with the **SocialGPT MCP server** (`https://mcp.gpt.social/mcp`).
The MCP provides the data; this skill provides the deterministic analysis and a
shareable report. If the SocialGPT tools below aren't available, the user needs
to connect the MCP first: https://gpt.social/integrations/mcp

## When to use

Trigger on requests like: *"what drives my views?"*, *"what's working on my
account?"*, *"what should I post more of?"*, *"do a performance audit"*, *"why
did some videos pop and others flop?"*

## Workflow

1. **Confirm access.** Make sure the SocialGPT MCP tools are connected. If
   `list_videos` isn't available, point the user to the connect page above and
   stop.

2. **Pull the data.** Call the MCP tool:
   ```
   list_videos(limit=50, sort="recent", include_analysis=false)
   ```
   To audit a single connected account, first call `list_accounts()` and pass
   its `account_id`. Save the **raw JSON** the tool returns to a file named
   `videos.json` in the working directory (the whole `{"videos": [...]}`
   envelope is fine — the script handles it).

3. **Run the analysis** (it has no third-party dependencies):
   ```
   python scripts/analyze.py videos.json
   ```
   The script reads `videos.json`, runs the tests, prints a Markdown summary to
   stdout, and writes `content-performance-report.html`.

4. **Relay the result.** Present the Markdown summary the script printed, then
   offer the user the generated `content-performance-report.html` to download /
   open (on Claude.ai it appears as a downloadable file).

## What the script does

For every video with a usable view count (Instagram posts showing 0 plays are
treated as missing, since IG hides reel plays), it tests each factor against
view count and ranks them by effect size and p-value:

- **Continuous factors** (video length, engagement rate) → Pearson correlation
  on log-views, with a real two-sided p-value.
- **Categorical factors** (platform, day of week, time of day, sequel vs.
  standalone) → Kruskal-Wallis rank test, robust to the heavy-tailed view
  distribution.

It flags factors at p<0.05 (significant) and p<0.01 (highly significant), then
translates the top significant factors into plain-English actions. See
`references/methodology.md` for the statistical details and caveats.

## Notes

- **Honest about samples.** With fewer than ~6 usable videos it will tell you so
  rather than invent findings. More posts → more statistical power; 30+ is ideal.
- **Correlation ≠ causation.** Significant factors are the best *hypotheses to
  test next*, not guarantees. The report says this explicitly.
- **Re-runnable.** Suggest the user re-run monthly; drivers shift as the account
  grows.
- **Part of a larger loop.** This is the "find your drivers" stage of the
  [**going-viral**](../going-viral) strategy loop — run it there to turn the
  drivers it surfaces into your next experiment.
