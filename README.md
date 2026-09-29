# Git agent

An independent Google ADK service that exposes A2A skills for Git research. It
uses MCP for tool access:

| Backend | Transport | Purpose |
| --- | --- | --- |
| [GitMCP](https://gitmcp.io/) | Hosted MCP Streamable HTTP endpoint over HTTPS | Public GitHub documentation and code search |
| [mcp-server-git](https://github.com/modelcontextprotocol/servers/tree/main/src/git) | Local stdio subprocess | Read-only status, branches, history, and diffs for one checkout |

GitMCP is already hosted. This service connects to it directly; it does not run
a GitMCP server. Although GitMCP's published examples still label the URL as
SSE, a live MCP handshake on 2026-09-29 rejected legacy SSE (`GET` returned
405) and succeeded with Streamable HTTP. This client therefore uses ADK's
`StreamableHTTPConnectionParams`. The local Git MCP process is optional and
starts only when `GIT_REPOSITORY_PATH` is set.

GitMCP does not execute arbitrary Git commands or work with private/local
checkouts. The generic URL can research public GitHub repositories selected in
the request; use a repository-specific URL to constrain the service to one
public repository. The local backend exposes a read-only subset of named Git
tools. It is not a shell command runner.

## Run locally

Requires Python 3.11+, `uv`, and credentials for the chosen ADK model. For
Gemini API key authentication, set `GOOGLE_API_KEY` in your environment.

```sh
uv sync --locked
uv run git-agent
curl http://localhost:8001/.well-known/agent-card.json
```

The A2A service listens on port 8001 by default. Its card advertises only the
skills enabled by the configured MCP backends. The concierge should discover
the card at `http://localhost:8001/.well-known/agent-card.json` and send A2A
requests to the URL advertised inside the card.

To target one public GitHub repository:

```sh
GITMCP_URL=https://gitmcp.io/OWNER/REPO uv run git-agent
```

To inspect a local Git checkout as well:

```sh
GIT_REPOSITORY_PATH=/absolute/path/to/repo uv run git-agent
```

To use only local Git tools, set `GITMCP_URL` to an empty string. The local MCP
server runs as a child process over stdio. When containerizing this mode, mount
only the intended repository into the agent container, preferably read-only.

| Variable | Default | Meaning |
| --- | --- | --- |
| `GITMCP_URL` | `https://gitmcp.io/docs` | Generic GitMCP endpoint; empty disables it |
| `GIT_REPOSITORY_PATH` | unset | Git checkout for local MCP operations |
| `GIT_AGENT_BASE_URL` | `http://localhost:8001` | A2A URL advertised to other services |
| `GIT_AGENT_MODEL` | `gemini-flash-latest` | ADK model name |
| `PORT` | `8001` | A2A listening port |

## Container and Helm

Build the image from this repository:

```sh
docker build -t git-agent:0.1.0 .
```

The chart in `charts/git-agent` deploys one replica using hosted GitMCP. Set
the image repository and tag to your published image, and provide model
credentials through a Kubernetes Secret or another supported ADK credential
mechanism. When using a Secret, set `existingSecret` to its name; it must have
a `GOOGLE_API_KEY` key.

```sh
helm upgrade --install git-agent charts/git-agent \
  --set image.repository=YOUR_REGISTRY/git-agent \
  --set image.tag=0.1.0 \
  --set existingSecret=YOUR_SECRET
```

The chart advertises an in-cluster service URL in the A2A card. The initial
single replica uses ADK's in-memory A2A task/session storage; configure shared
storage before scaling to multiple replicas.

## Current boundaries

- GitMCP covers public GitHub research; it is a different product from the
  local `mcp-server-git` package.
- Local tools are read-only by tool allowlist. For a strong repository boundary,
  isolate the service with filesystem permissions or a container mount.
- The A2A card and HTTP route can be tested without model credentials. A live
  research request needs model credentials and outbound network access.
