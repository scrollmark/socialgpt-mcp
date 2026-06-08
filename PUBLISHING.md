# Publishing & listing the SocialGPT MCP server

This repo is the public front door for a **remote** MCP server (`https://mcp.gpt.social/mcp`). Getting it listed has two independent tracks, and this repo is set up for **both**:

1. **The official MCP registry** (`registry.modelcontextprotocol.io`) — the canonical, machine-readable registry backed by Anthropic/GitHub/Microsoft. Driven by [`server.json`](./server.json).
2. **Third-party directories** (mcpservers.com, mcp.so, glama.ai, PulseMCP, …) — human-browsable catalogs that index public GitHub repos and/or the official registry.

> **Why a repo at all for a remote server?** Directories hard-require a public, browsable GitHub URL, and the official registry uses the repo as the namespace anchor for `io.github.scrollmark/*`. None of this exposes the private monorepo — this repo holds only docs + `server.json`.

---

## Decisions baked into this repo

| Field | Value | Where |
|-------|-------|-------|
| Repo | `github.com/scrollmark/socialgpt-mcp` | this repo |
| Registry namespace (server name) | `io.github.scrollmark/socialgpt` | `server.json` → `name` |
| Endpoint | `https://mcp.gpt.social/mcp` (streamable-http) | `server.json` → `remotes` |
| License | MIT | `LICENSE` |

The `io.github.scrollmark` namespace is verified **just by owning the repo under the `scrollmark` org** — no DNS records, no `.well-known` files. (If you ever want the on-brand `social.gpt/socialgpt` name instead, that path needs a DNS TXT record on `gpt.social`; it's a one-line change to `name` plus domain verification. Not required, and not done here.)

---

## Track 1 — Official MCP registry

### Prerequisites
- This repo pushed public to `github.com/scrollmark/socialgpt-mcp`.
- The endpoint `https://mcp.gpt.social/mcp` reachable on the public internet (the registry requires remote servers to be publicly accessible).

### Option A — one-off publish from your machine

```bash
# 1. Install the publisher CLI
brew install mcp-publisher
#   …or, without Homebrew:
#   curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/

# 2. From the repo root (where server.json lives), authenticate with GitHub.
#    The account you log in with must be a member/owner of the scrollmark org
#    so it can claim the io.github.scrollmark namespace.
mcp-publisher login github

# 3. Publish
mcp-publisher publish
```

`mcp-publisher` reads `server.json` from the current directory. (`mcp-publisher init` can regenerate/validate it, but the committed file is already schema-valid — don't let it overwrite the curated description.)

### Option B — automated via GitHub Actions (recommended for an org repo)

A workflow is included at [`.github/workflows/publish-mcp.yml`](./.github/workflows/publish-mcp.yml). It authenticates with **GitHub OIDC** — no personal login, no stored token — and the registry binds the `io.github.scrollmark` namespace to the repo's owner (`scrollmark`). Publish by pushing a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

### Updating the listing later
Bump `version` in `server.json` (and the endpoint/description if they change), then re-run the publish (or push a new `vX.Y.Z` tag). The registry treats each `version` as immutable, so always increment it.

### Verify
After publishing:

```bash
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.scrollmark/socialgpt" | jq
```

---

## Track 2 — Third-party directories

Most directories either ingest the official registry automatically or take a GitHub URL / short submission form. Once Track 1 is live, several of these pick it up with no extra work.

| Directory | How to submit |
|-----------|---------------|
| **mcpservers.com** | Submit `github.com/scrollmark/socialgpt-mcp` via their "Add server" form. |
| **mcp.so** | Submit the repo URL via the "Submit" link. |
| **glama.ai/mcp** | Indexes public GitHub repos with MCP metadata; can also be submitted manually. |
| **PulseMCP** | Mirrors the official registry — usually no action needed after Track 1; otherwise use their submit form. |
| **Awesome MCP Servers** (GitHub list) | Open a PR adding a one-line entry pointing at this repo. |

Keep the pitch consistent with the README: *"Your social analytics, video analysis, and competitor intel inside any MCP client — OAuth, read-only, hosted."*

---

## Pre-publish checklist

- [ ] Repo is public at `github.com/scrollmark/socialgpt-mcp`.
- [ ] `https://mcp.gpt.social/mcp` is live and completes an OAuth 2.1 handshake from a fresh client.
- [ ] `server.json` validates (the `$schema` URL is current as of 2025-12-11).
- [ ] `name` namespace (`io.github.scrollmark/socialgpt`) matches the org that owns the repo.
- [ ] `version` is correct and not previously published.
- [ ] README setup snippets actually connect from at least one client (Claude Desktop or Claude Code).
