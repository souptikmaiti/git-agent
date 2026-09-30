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
root. Set `GOOGLE_API_KEY`, `GITHUB_MCP_TOKEN`, and `A2A_TASK_DATABASE_URL`. Use
the `git_agent_tasks` database in your local PostgreSQL container. The GitHub
token must come from the GitHub
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

The agent's Docker container cannot use `127.0.0.1` to reach other containers.
Put GitHub MCP, PostgreSQL, and the agent on a shared Docker network. Copy
`.env` to the ignored `.env.container` and set `GITHUB_MCP_URL` to
`http://github-mcp:8082/` and `A2A_TASK_DATABASE_URL` to a URL using
`a2a-postgres:5432` as the host. For example:

```sh
docker network create agents
docker network connect agents github-mcp
docker network connect agents a2a-postgres
cp .env .env.container
# Edit .env.container with the two container-reachable URLs.
docker build -t git-agent:0.1.0 .
docker run --rm --network agents -p 127.0.0.1:8001:8001 \
  --env-file .env.container \
  git-agent:0.1.0
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `GITHUB_MCP_URL` | `http://127.0.0.1:8082/` | Required GitHub MCP Streamable HTTP endpoint |
| `GITHUB_MCP_TOKEN` | unset | Bearer token sent to GitHub MCP; required for private repositories |
| `GIT_AGENT_BASE_URL` | `http://localhost:8001` | A2A URL advertised to other services |
| `GIT_AGENT_MODEL` | `gemini-3.6-flash` | ADK model name |
| `GIT_AGENT_TEMPERATURE` | `1.0` | Model sampling temperature (0 to 1) |
| `A2A_TASK_DATABASE_URL` | `postgresql+asyncpg://postgres@127.0.0.1:5432/git_agent_tasks` | PostgreSQL URL shared by A2A tasks and ADK sessions; set the password in `.env` |
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
values may name the same Secret. Set `existingTaskDatabaseSecret` to a Secret
containing a PostgreSQL `A2A_TASK_DATABASE_URL`, for example
`postgresql+asyncpg://user:password@postgres-host:5432/git_agent_tasks`.
Create that database and user before starting the agent. The task and session
tables are created automatically.

```sh
helm upgrade --install git-agent charts/git-agent \
  --set image.repository=YOUR_REGISTRY/git-agent \
  --set image.tag=0.1.0 \
  --set githubMcpUrl=http://github-mcp.YOUR_NAMESPACE.svc.cluster.local:8082/ \
  --set existingSecret=YOUR_MODEL_SECRET \
  --set existingGithubMcpSecret=YOUR_GITHUB_SECRET \
  --set existingTaskDatabaseSecret=YOUR_TASK_DATABASE_SECRET
```

Local and Kubernetes runs both use PostgreSQL. The local `.env.example` points
to the Docker PostgreSQL instance on `127.0.0.1:5432`; replace its sample
password in your `.env`. The Kubernetes Secret must point to a database
reachable from the agent pod, not to pod-local `127.0.0.1`. Use a separate
database for each agent service. A2A tasks and ADK session history survive
restarts; an interrupted run is not resumed automatically. ADK artifacts,
memory, and credentials remain in memory. Use TLS when the MCP connection
crosses a trusted local network boundary.

## Boundaries

- GitHub MCP exposes named GitHub API tools, not arbitrary shell Git commands.
- The A2A card and HTTP route can be tested without model credentials. A live
  research request needs a model credential and connectivity to GitHub MCP.
- The configured Gemini API receives repository excerpts selected for model
  context. A fully on-premise deployment requires an on-premise model too.
