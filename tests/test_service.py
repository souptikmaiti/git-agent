from pathlib import Path

from starlette.testclient import TestClient

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
