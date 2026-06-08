#!/usr/bin/env bash
# Add the SocialGPT MCP server to Claude Code.
# On first use, Claude Code opens a browser for OAuth sign-in and caches the token locally.
claude mcp add --transport http socialgpt https://mcp.gpt.social/mcp
