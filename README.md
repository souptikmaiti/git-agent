# Git agent

An independently deployed Google ADK service that exposes A2A skills for Git
research. It uses the [GitHub MCP Server](https://github.com/github/github-mcp-server)
over Streamable HTTP to search and read repositories accessible to its
credential, including private GitHub Enterprise repositories.

Run the GitHub MCP Server separately in HTTP mode. The agent connects to its
`GITHUB_MCP_URL` and sends `Authorization: Bearer <GITHUB_MCP_TOKEN>` on MCP
requests. Configure the GitHub Enterprise host with `GITHUB_HOST` **on the MCP
server**; do not put a GitHub repository URL in `GITHUB_MCP_URL`. The agent's
GitHub tool allowlist includes only repository search, code and file reads,
branches, commits, and tags. Keep the MCP server in read-only mode too.

## Run locally

Requires Python 3.11+, `uv`, a running GitHub MCP Server, and credentials for
the configured ADK model. Copy `.env.example` to `.env` in this repository's
root. Set `GOOGLE_API_KEY` and `GITHUB_MCP_TOKEN` using a token from the GitHub
instance configured on the MCP server. Limit that token to the repositories and
read permissions the agent needs. `.env` is ignored by Git; existing process
environment variables take precedence.

```sh
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY and GITHUB_MCP_TOKEN.
uv sync --locked
uv run git-agent
curl http://localhost:8001/.well-known/agent-card.json
```

With the local GitHub MCP container from the setup guide, use
`GITHUB_MCP_URL=http://127.0.0.1:8082/`. The A2A service listens on port 8001.
The concierge can discover its card at
`http://localhost:8001/.well-known/agent-card.json` and use the A2A URL in the
card. The card and service can start without a GitHub token, but private
repository tool calls require one.

The agent's Docker container cannot use `127.0.0.1` to reach a different
container. Put the two containers on a shared Docker network and set
`GITHUB_MCP_URL=http://github-mcp:8082/` in the agent container. For example:

```sh
docker network create agents
docker network connect agents github-mcp
docker build -t git-agent:0.1.0 .
docker run --rm --network agents -p 127.0.0.1:8001:8001 \
  --env-file .env \
  -e GITHUB_MCP_URL=http://github-mcp:8082/ \
  git-agent:0.1.0
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `GITHUB_MCP_URL` | `http://127.0.0.1:8082/` | Required GitHub MCP Streamable HTTP endpoint |
| `GITHUB_MCP_TOKEN` | unset | Bearer token sent to GitHub MCP; required for private repositories |
| `GIT_AGENT_BASE_URL` | `http://localhost:8001` | A2A URL advertised to other services |
| `GIT_AGENT_MODEL` | `gemini-3.6-flash` | ADK model name |
| `GIT_AGENT_TEMPERATURE` | `1.0` | Model sampling temperature (0 to 1) |
| `PORT` | `8001` | A2A listening port |

Google recommends the default temperature of 1.0 for Gemini 3 models because
lower values can cause looping or weaker reasoning in some tasks. See the
[Gemini 3 guidance](https://ai.google.dev/gemini-api/docs/gemini-3#temperature).

## Helm

The chart in `charts/git-agent` deploys one agent replica. Deploy GitHub MCP
separately as a service reachable from the agent pod. Set `githubMcpUrl` to
that service's URL, and supply model and GitHub credentials through Kubernetes
Secrets. `existingSecret` must contain `GOOGLE_API_KEY`;
`existingGithubMcpSecret` must contain `GITHUB_MCP_TOKEN` by default. The two
values may name the same Secret.

```sh
helm upgrade --install git-agent charts/git-agent \
  --set image.repository=YOUR_REGISTRY/git-agent \
  --set image.tag=0.1.0 \
  --set githubMcpUrl=http://github-mcp.YOUR_NAMESPACE.svc.cluster.local:8082/ \
  --set existingSecret=YOUR_MODEL_SECRET \
  --set existingGithubMcpSecret=YOUR_GITHUB_SECRET
```

The chart advertises an in-cluster service URL in the A2A card. Its initial
single replica uses ADK's in-memory A2A task/session storage; configure shared
storage before scaling to multiple replicas. Use TLS when the MCP connection
crosses a trusted local network boundary.

## Boundaries

- GitHub MCP exposes named GitHub API tools, not arbitrary shell Git commands.
- The A2A card and HTTP route can be tested without model credentials. A live
  research request needs a model credential and connectivity to GitHub MCP.
- The configured Gemini API receives repository excerpts selected for model
  context. A fully on-premise deployment requires an on-premise model too.
