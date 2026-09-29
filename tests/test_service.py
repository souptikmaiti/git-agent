from pathlib import Path

from starlette.testclient import TestClient

from git_agent.agent import build_agent
from git_agent.config import Settings
from git_agent.server import build_app


def test_card_advertises_only_enabled_skills(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    settings = Settings(gitmcp_url="", git_repository_path=tmp_path)

    with TestClient(build_app(settings)) as client:
        response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert [skill["id"] for skill in card["skills"]] == ["local_git_inspection"]
    assert card["supportedInterfaces"][0]["url"] == settings.public_base_url


def test_requires_one_mcp_backend():
    settings = Settings(gitmcp_url="")

    try:
        settings.validate()
    except ValueError as error:
        assert "GITMCP_URL or GIT_REPOSITORY_PATH" in str(error)
    else:
        raise AssertionError("empty MCP configuration should fail")


def test_model_and_temperature_are_passed_to_adk():
    agent = build_agent(Settings())

    assert agent.model == "gemini-3.6-flash"
    assert agent.generate_content_config.temperature == 0


def test_settings_load_repo_local_env(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        "GIT_AGENT_MODEL=gemini-3.6-flash\nGIT_AGENT_TEMPERATURE=0.25\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GIT_AGENT_MODEL", raising=False)
    monkeypatch.delenv("GIT_AGENT_TEMPERATURE", raising=False)

    settings = Settings.from_env()

    assert settings.model == "gemini-3.6-flash"
    assert settings.temperature == 0.25
