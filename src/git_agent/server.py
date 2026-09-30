"""A2A application and CLI entry point."""

from contextlib import asynccontextmanager

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.artifacts import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
import uvicorn

from git_agent.agent import build_agent
from git_agent.config import Settings
from git_agent.task_store import create_task_store


def build_card(settings: Settings) -> AgentCard:
    skills = [
        AgentSkill(
            id="github_code_research",
            name="GitHub code research",
            description="Search and inspect accessible public or private GitHub repositories.",
            tags=["git", "github", "code-search", "repository"],
            examples=["How is request routing implemented in owner/repository?"],
        )
    ]

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
    agent = build_agent(settings)
    task_store, task_lifespan = create_task_store(settings.a2a_task_database_url)
    session_service = DatabaseSessionService(db_engine=task_store.engine)
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )

    @asynccontextmanager
    async def lifespan(app):
        async with task_lifespan(app):
            try:
                await session_service.prepare_tables()
                yield
            finally:
                await runner.close()

    return to_a2a(
        agent,
        agent_card=build_card(settings),
        port=settings.port,
        task_store=task_store,
        runner=runner,
        lifespan=lifespan,
    )


app = build_app(Settings.from_env())


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run("git_agent.server:app", host="0.0.0.0", port=settings.port)
