from pathlib import Path

from starlette.testclient import TestClient

from git_agent.agent import build_agent
from git_agent.config import Settings
from git_agent.server import build_app


def test_card_advertises_github_skill():
    settings = Settings()

    with TestClient(build_app(settings)) as client:
        response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert [skill["id"] for skill in card["skills"]] == ["github_code_research"]
    assert card["supportedInterfaces"][0]["url"] == settings.public_base_url


def test_requires_github_mcp_url():
    settings = Settings(github_mcp_url="")

    try:
        settings.validate()
    except ValueError as error:
        assert "GITHUB_MCP_URL is required" in str(error)
    else:
        raise AssertionError("empty MCP configuration should fail")


def test_model_and_temperature_are_passed_to_adk():
    agent = build_agent(Settings())

    assert agent.model == "gemini-3.6-flash"
    assert agent.generate_content_config.temperature == 1.0


def test_github_mcp_uses_bearer_token_and_read_only_tools():
    settings = Settings(
        github_mcp_url="http://127.0.0.1:8082/",
        github_mcp_token="test-token",
    )
    agent = build_agent(settings)

    assert len(agent.tools) == 1
    toolset = agent.tools[0]
    assert toolset._connection_params.url == "http://127.0.0.1:8082/"
    assert toolset._connection_params.headers == {
        "Authorization": "Bearer test-token"
    }
    assert "search_repositories" in toolset.tool_filter
    assert "create_repository" not in toolset.tool_filter
    assert "test-token" not in agent.instruction
    assert "test-token" not in repr(settings)


def test_settings_load_local_env(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        "GIT_AGENT_MODEL=gemini-3.6-flash\n"
        "GIT_AGENT_TEMPERATURE=0.25\n"
        "GITHUB_MCP_URL=http://github-mcp:8082/\n"
        "GITHUB_MCP_TOKEN=test-token\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GIT_AGENT_MODEL", raising=False)
    monkeypatch.delenv("GIT_AGENT_TEMPERATURE", raising=False)
    monkeypatch.delenv("GITHUB_MCP_URL", raising=False)
    monkeypatch.delenv("GITHUB_MCP_TOKEN", raising=False)

    settings = Settings.from_env()

    assert settings.model == "gemini-3.6-flash"
    assert settings.temperature == 0.25
    assert settings.github_mcp_url == "http://github-mcp:8082/"
    assert settings.github_mcp_token == "test-token"
