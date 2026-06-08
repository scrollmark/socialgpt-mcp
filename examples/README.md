# Example client configs

Ready-to-copy MCP configuration for the SocialGPT server (`https://mcp.gpt.social/mcp`).
Pick the file for your client; full instructions are in the [root README](../README.md#setup).

| Client | File | Where it goes |
|--------|------|---------------|
| Claude Desktop | [`claude-desktop.json`](./claude-desktop.json) | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| Claude Code | [`claude-code.sh`](./claude-code.sh) | run the command in your terminal |
| Cursor | [`cursor.json`](./cursor.json) | `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) |
| VS Code | [`vscode.json`](./vscode.json) | `.vscode/mcp.json` |
| Codex | [`codex.toml`](./codex.toml) | `~/.codex/config.toml` or `.codex/config.toml` |
| AntiGravity | [`antigravity.json`](./antigravity.json) | `~/.gemini/config/mcp_config.json` |
| ChatGPT / Claude.ai / other | — | paste the URL `https://mcp.gpt.social/mcp` in the client's "add MCP server" UI |

All clients authenticate via OAuth 2.1 + PKCE — you sign in to your SocialGPT account once, no API keys.
