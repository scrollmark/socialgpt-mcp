<div align="center">

<img src="./assets/logo.png" width="96" alt="SocialGPT logo" />

# SocialGPT MCP Server

**Your social data, inside every AI tool.**

Connect [SocialGPT](https://gpt.social) to Claude, ChatGPT, Cursor, and any AI agent that speaks the [Model Context Protocol](https://modelcontextprotocol.io). Your analytics, video analysis, and content intelligence — available everywhere you work.

[![Model Context Protocol](https://img.shields.io/badge/MCP-compatible-7137FF)](https://modelcontextprotocol.io)
[![Auth](https://img.shields.io/badge/auth-OAuth_2.1_+_PKCE-10A37F)](#authentication--scopes)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

[Setup](#setup) · [Tools](#tools) · [Guided workflows](#guided-workflows) · [Authentication](#authentication--scopes) · [Roadmap](#roadmap)

</div>

---

## What is this?

This is the public front door for the **SocialGPT MCP server** — a hosted, remote MCP server that brings your social media analytics into any MCP-compatible AI agent. There's nothing to install and no API keys to manage: you point your client at one URL and authenticate once with your SocialGPT account.

**Connection URL:**

```
https://mcp.gpt.social/mcp
```

- **Transport:** Streamable HTTP
- **Auth:** OAuth 2.1 with PKCE — sign in once with your SocialGPT account, revoke any time
- **Access:** Read-only analytics by default; an optional scope lets agents pull new content into your library for analysis

> New to SocialGPT? [Create a free account](https://app.gpt.social/signup), then [connect a social account](https://app.gpt.social/account) to unlock analysis of your own content. Public/competitor analysis works without connecting anything.

---

## Setup

Pick your client, paste the config, and authenticate with your SocialGPT account. Most clients open a browser window for OAuth the first time an agent uses a SocialGPT tool.

Ready-to-copy config files for each client live in [`examples/`](./examples).

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS), then restart Claude Desktop:

```json
{
  "mcpServers": {
    "socialgpt": {
      "url": "https://mcp.gpt.social/mcp"
    }
  }
}
```

### Claude.ai

Settings → **Integrations** → **Add more** → paste the URL and follow the prompts:

```
https://mcp.gpt.social/mcp
```

Claude.ai handles authentication during the integration setup flow.

### Claude Code

```bash
claude mcp add --transport http socialgpt https://mcp.gpt.social/mcp
```

On your first request that uses SocialGPT tools, Claude Code opens a browser for OAuth sign-in and caches the token locally.

### Cursor

Add to your project's `.cursor/mcp.json`, or `~/.cursor/mcp.json` for global access:

```json
{
  "mcpServers": {
    "socialgpt": {
      "url": "https://mcp.gpt.social/mcp"
    }
  }
}
```

### VS Code

Add to `.vscode/mcp.json` in your workspace (or run **MCP: Add Server** from the command palette):

```json
{
  "servers": {
    "socialgpt": {
      "type": "http",
      "url": "https://mcp.gpt.social/mcp"
    }
  }
}
```

### ChatGPT

Settings → **Tools & integrations** → **Add MCP server**, then paste the URL:

```
https://mcp.gpt.social/mcp
```

### Codex

Add to `~/.codex/config.toml` (or `.codex/config.toml` for a single project):

```toml
[mcp_servers.socialgpt]
url = "https://mcp.gpt.social/mcp"
```

### Cline

**MCP Servers** icon → **Remote Servers** → add the server URL, or edit `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "socialgpt": {
      "type": "streamableHttp",
      "url": "https://mcp.gpt.social/mcp"
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "socialgpt": {
      "serverUrl": "https://mcp.gpt.social/mcp"
    }
  }
}
```

### AntiGravity

Add to `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "socialgpt": {
      "serverUrl": "https://mcp.gpt.social/mcp"
    }
  }
}
```

### Any other MCP client

Any client that supports the Model Context Protocol can connect using the server URL `https://mcp.gpt.social/mcp`. Check your client's docs for where to register an MCP server, and use the **streamable HTTP** transport.

---

## What you can do

| | |
|---|---|
| **Your content** | Full visibility into your own posts and performance — list and search your analyzed videos, deep-dive analysis with hooks, themes, and transcripts, and track views, engagement, and growth over time across TikTok, Instagram, and YouTube. |
| **Competitor intel** | Reverse-engineer what works in any niche — look up any public creator's profile and content DNA, browse their top and recent videos, find videos similar to yours, and benchmark against comparable creators. |
| **Content profile** | Your content DNA, always up to date — synthesized pillars and recurring themes, a voice and tone profile derived from your actual content, and a prescriptive playbook that evolves as you create. |
| **Guided workflows** | Pre-built prompts that chain tools together for a full performance audit, head-to-head benchmarking, or reverse-engineering a creator's winning formula. |

### Just ask

Once connected, talk to your agent like a teammate:

> *"How did my content perform this month compared to last?"*
>
> *"Find creators in the fitness niche on TikTok and show me what's working for them."*
>
> *"Analyze my latest Instagram reel and suggest better hooks."*
>
> *"Compare my engagement rate to similar creators on YouTube."*

---

## Tools

The server exposes a curated, mostly read-only surface. The **Scope** column shows which OAuth scope each tool needs (see [Authentication & scopes](#authentication--scopes)).

#### Your videos & content

| Tool | Description | Scope |
|------|-------------|-------|
| `list_videos` | List your videos — filter by platform/query, scope to one connected account, sort by recent or top performers. | `analysis:read` |
| `search_videos` | Search your analyzed videos by query. | `analysis:read` |
| `get_video` | Get one video by platform + post id — owned or public/analyzed. | `analysis:read` · `analysis:read:public` |
| `get_video_analysis` | Full analysis (incl. scene breakdown) for a video — owned or competitor. | `analysis:read` · `analysis:read:public` |
| `search` | Search your content (connector-convention entrypoint). | `analysis:read` |
| `fetch` | Fetch a single resource by id (connector-convention entrypoint). | `analysis:read` |
| `get_content_profile` | Your content DNA — topics, pillars, and voice synthesized from your content. | `analysis:read` |

#### Accounts & metrics

| Tool | Description | Scope |
|------|-------------|-------|
| `list_accounts` | List your connected social accounts. | `analysis:read` |
| `get_account` | Get one connected account by id. | `analysis:read` |
| `get_account_metrics` | Views / engagement as a time series over a trailing window (up to 365 days), per account or aggregated. | `analysis:read` |

#### Competitor & creator discovery

| Tool | Description | Scope |
|------|-------------|-------|
| `get_creator` | Get a public/competitor creator's profile by platform + handle. | `analysis:read:public` |
| `list_creator_videos` | List a public creator's videos, sorted by recent or top, optionally with analysis. | `analysis:read:public` |
| `list_similar_videos` | Find videos similar to a given one from across the platform. | `analysis:read` · `analysis:read:public` |

#### Analyze new content

| Tool | Description | Scope |
|------|-------------|-------|
| `analyze_post` | Analyze a single TikTok/YouTube/Instagram post by URL — adds it to your library and runs deep video analysis. | `content:ingest` |
| `analyze_creator` | Analyze a public creator's recent posts (async — returns a `job_id` to poll). | `content:ingest` |
| `get_analysis_status` | Check the status of an `analyze_creator` job. | `content:ingest` |

#### Meta

| Tool | Description | Scope |
|------|-------------|-------|
| `server_info` | Basic info about the server and the scopes it supports. | — |
| `whoami` | The authenticated caller — user id and granted scopes. | — |

---

## Guided workflows

The server also ships **prompts** — guided workflows that chain the tools above into a complete analysis. Clients surface these as slash-commands or prompt templates.

| Prompt | What it does |
|--------|--------------|
| `analyze_my_account` | A thorough performance audit of one connected account over a timeframe — momentum, what's working, what's underperforming, and prioritized recommendations. |
| `compare_to_similar` | Benchmark one of your videos head-to-head against similar competitor videos and get specific changes to test. |
| `what_works_in_niche` | Reverse-engineer a creator's winning formula — hooks, formats, topics, cadence — into a repeatable playbook. |
| `connect_account` | Guided setup for linking a social account to unlock analysis of your own content. |

---

## Skills

Where prompts *ask* the model to do an analysis, **[skills](./skills)** ship the
work itself. Most are a real script the agent runs on your MCP data, returning a
styled report; **going-viral** is the strategy loop that conducts the others.
They install on Claude.ai (upload a zip) and Claude Code (drop in a folder), and
run the same SocialGPT MCP tools under the hood.

| Skill | Answers | Tools used |
|-------|---------|------------|
| [`going-viral`](./skills/going-viral) | *"How do I actually go viral?"* — the end-to-end loop: research outliers, find your own drivers, study winning hooks, ship one experiment, review, repeat. Grounds each step in your data and routes into the three analysis skills. | orchestrates — `list_videos`, `list_creator_videos`, `get_video_analysis`, `get_content_profile`, `get_growth_summary`, … |
| [`content-performance-audit`](./skills/content-performance-audit) | *"What actually drives my views?"* — a statistical audit of your posts (length, timing, platform, format) with real significance tests. | `list_videos` |
| [`competitor-gap-analysis`](./skills/competitor-gap-analysis) | *"Where are competitors winning that I'm silent?"* — content gaps, owned territory, format gaps vs. 1–3 rivals. | `list_videos`, `list_creator_videos` |
| [`hook-retention-teardown`](./skills/hook-retention-teardown) | *"What do my best hooks do that my flops don't?"* — pacing and language patterns separating winners from losers. | `list_videos`, `get_video_analysis` |

See **[`skills/`](./skills)** for install instructions, the build script, and the
methodology behind each one. New skills land here as the tool surface grows.

---

## Authentication & scopes

The SocialGPT MCP server is an OAuth 2.1 **resource server**. Your client performs an OAuth 2.1 + PKCE flow against your SocialGPT account; the server validates the bearer token on every request. No API keys are ever copied around, and you can revoke access at any time from your SocialGPT settings.

Access is governed by three scopes:

| Scope | Grants |
|-------|--------|
| `analysis:read` | Read **your own** content, metrics, connected accounts, and content profile. |
| `analysis:read:public` | Read **public/competitor** creators and their analysis. |
| `content:ingest` | Trigger analysis of new posts/creators — pulls content **into your library** for analysis. This is the only non-read scope; it does **not** post or publish anything on your behalf. |

Until you [connect a social account](https://app.gpt.social/account), only public/competitor analysis is available. Newly connected accounts appear automatically on the same token — no need to re-authenticate.

---

## Roadmap

Read access is live today. We're building **write** capabilities so your agent can act, not just analyze — all over the same MCP connection:

- **Publish content** — post directly to TikTok, Instagram, and YouTube from any AI agent
- **Schedule posts** — queue content for optimal posting times
- **Generate scripts** — full video scripts grounded in your analytics and style
- **Build carousels** — design and publish carousel posts powered by your content DNA
- **Manage comments** — read, reply to, and moderate comments across platforms
- **A/B test hooks** — run experiments on hooks and captions

---

## Support & links

⭐ **If SocialGPT MCP is useful to you, [star this repo](https://github.com/scrollmark/socialgpt-mcp)** — it helps other creators discover it.

- **Product:** [gpt.social](https://gpt.social) · [MCP integration page](https://gpt.social/integrations/mcp)
- **Sign up:** [app.gpt.social/signup](https://app.gpt.social/signup)
- **Connect accounts:** [app.gpt.social/account](https://app.gpt.social/account)
- **Learn about MCP:** [modelcontextprotocol.io](https://modelcontextprotocol.io)

This repository contains the public listing and connection details for the SocialGPT MCP server. The server itself is hosted by SocialGPT; its source is not part of this repository.

## License

[MIT](./LICENSE) © Scrollmark, Inc.
