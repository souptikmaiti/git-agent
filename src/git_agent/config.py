"""Configuration for the independently deployed Git agent."""

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    gitmcp_url: str = "https://gitmcp.io/docs"
    git_repository_path: Path | None = None
    public_base_url: str = "http://localhost:8001"
    model: str = "gemini-flash-latest"
    port: int = 8001

    @classmethod
    def from_env(cls) -> "Settings":
        repo = os.getenv("GIT_REPOSITORY_PATH", "").strip()
        settings = cls(
            gitmcp_url=os.getenv("GITMCP_URL", "https://gitmcp.io/docs").strip(),
            git_repository_path=Path(repo).expanduser().resolve() if repo else None,
            public_base_url=os.getenv(
                "GIT_AGENT_BASE_URL", "http://localhost:8001"
            ).strip(),
            model=os.getenv("GIT_AGENT_MODEL", "gemini-flash-latest"),
            port=int(os.getenv("PORT", "8001")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.gitmcp_url and self.git_repository_path is None:
            raise ValueError("Configure GITMCP_URL or GIT_REPOSITORY_PATH")
        for name, value in (
            ("GITMCP_URL", self.gitmcp_url),
            ("GIT_AGENT_BASE_URL", self.public_base_url),
        ):
            if value and (
                urlparse(value).scheme not in {"http", "https"}
                or not urlparse(value).netloc
            ):
                raise ValueError(f"{name} must be an HTTP(S) URL")
        if self.git_repository_path is not None and not (
            self.git_repository_path / ".git"
        ).exists():
            raise ValueError("GIT_REPOSITORY_PATH must point to a Git checkout")
        if not 1 <= self.port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
