<div align="center">

# SocialGPT Skills

**Powered-up workflows that turn the [SocialGPT MCP](../README.md) into a content strategist.**

Install once, then just ask — your agent pulls your real data through the MCP
and runs a deterministic analysis with a shareable report.

</div>

---

## What is a skill?

An [Agent Skill](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
is a folder with a `SKILL.md` (instructions) plus optional scripts the agent can
run. These skills **pair with the SocialGPT MCP server**: the MCP provides your
data, the skill provides what a prompt can't do reliably on its own — a real
statistical model, a deterministic report, or the strategy loop that ties them
together — and hands you back a styled HTML summary or a grounded plan.

Same format runs on **Claude.ai** and **Claude Code** (and any agent that
supports Agent Skills). Author once, install anywhere.

> **Prerequisite:** connect the SocialGPT MCP first →
> [gpt.social/integrations/mcp](https://gpt.social/integrations/mcp).
> The skills call MCP tools like `list_videos`; without the connection they have
> no data to work on.

## The skills

| Skill | Answers | MCP tools it uses |
|-------|---------|-------------------|
| [**going-viral**](./going-viral) | *"How do I actually go viral?"* — the end-to-end loop that conducts the three skills below: research outliers, find your own drivers, study winning hooks, ship one experiment, review, repeat. | orchestrates — `list_videos`, `list_creator_videos`, `get_video_analysis`, `get_content_profile`, `get_growth_summary`, … |
| [**content-performance-audit**](./content-performance-audit) | *"What actually drives my views?"* — a statistical audit of your own posts (length, timing, platform, format) with real significance tests. | `list_videos` |
| [**competitor-gap-analysis**](./competitor-gap-analysis) | *"Where are competitors winning that I'm silent?"* — content gaps, owned territory, and format gaps vs. 1–3 rivals. | `list_videos`, `list_creator_videos` |
| [**hook-retention-teardown**](./hook-retention-teardown) | *"What do my best hooks do that my flops don't?"* — pacing and language patterns separating your winners from losers. | `list_videos`, `get_video_analysis` |

The three analysis skills are each a self-contained folder: a `SKILL.md`, a
`scripts/analyze.py` (Python **standard library only** — no pip install), and a
`references/methodology.md`. **going-viral** is an *orchestrator* skill — a
`SKILL.md` plus an 18-file `references/` playbook, no script — that conducts the
analysis skills and the MCP tools through the full viral loop.

## Install

### Claude.ai (web / desktop)

1. **Get the bundle.** Download a skill `.zip` from
   [gpt.social/integrations/mcp/skills](https://gpt.social/integrations/mcp/skills),
   or build them yourself (below).
2. **Turn on code execution.** Settings → **Capabilities** → enable the code /
   analysis tool (skills run their scripts in Claude's sandbox).
3. **Upload the skill.** Settings → **Capabilities → Skills → Upload skill**, and
   pick the `.zip`. (The zip contains a folder with a `SKILL.md` at its root.)
4. **Just ask** — e.g. *"what drives my views?"* Claude loads the skill, calls
   the SocialGPT MCP, runs the analysis, and hands you the report.

### Claude Code

Drop a skill folder into your skills directory:

```bash
git clone https://github.com/scrollmark/socialgpt-mcp
cp -r socialgpt-mcp/skills/content-performance-audit ~/.claude/skills/   # personal
# or  .claude/skills/  inside a project
```

Make sure the SocialGPT MCP is added (`claude mcp add --transport http socialgpt https://mcp.gpt.social/mcp`),
then ask for an audit.

## Build the bundles yourself

```bash
python skills/build.py            # vendor the shared lib + write dist/<skill>.zip
python skills/build.py --check    # CI: verify the vendored libs are in sync
```

The shared helpers in [`_shared/sgpt_lib.py`](./_shared/sgpt_lib.py) (stats +
report rendering) are vendored into each skill's `scripts/` so every skill folder
is independently installable. `build.py` keeps those copies in sync and zips each
skill into `dist/`.

## Safety

Skills run code. These are **MIT-licensed and fully auditable** — every script is
plain-Python, standard-library-only, and reads only the data your MCP connection
already exposes. Read `scripts/analyze.py` before you install, the same as you
would any skill.
