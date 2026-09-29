"""A2A application and CLI entry point."""

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn

from git_agent.agent import build_agent
from git_agent.config import Settings


def build_card(settings: Settings) -> AgentCard:
    skills: list[AgentSkill] = []
    if settings.gitmcp_url:
        skills.append(
            AgentSkill(
                id="github_code_research",
                name="Public GitHub code research",
                description="Search public GitHub repository documentation and code.",
                tags=["git", "github", "code-search", "documentation"],
                examples=[
                    "How is request routing implemented in owner/repository?"
                ],
            )
        )
    if settings.git_repository_path is not None:
        skills.append(
            AgentSkill(
                id="local_git_inspection",
                name="Local Git inspection",
                description="Read status, branches, commit history, and diffs of the configured checkout.",
                tags=["git", "status", "history", "diff"],
                examples=["Show recent commits and uncommitted changes."],
            )
        )

    return AgentCard(
        name="git_agent",
        description="Git and GitHub research service backed by MCP tools.",
        supported_interfaces=[
            AgentInterface(
                url=settings.public_base_url.rstrip("/"),
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=skills,
    )


def build_app(settings: Settings):
    settings.validate()
    return to_a2a(
        build_agent(settings),
        agent_card=build_card(settings),
        port=settings.port,
    )


app = build_app(Settings.from_env())


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run("git_agent.server:app", host="0.0.0.0", port=settings.port)
