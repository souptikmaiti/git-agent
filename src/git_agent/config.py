"""Configuration for the independently deployed Git agent."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    github_mcp_url: str = "http://127.0.0.1:8082/"
    github_mcp_token: str = field(default="", repr=False)
    public_base_url: str = "http://localhost:8001"
    model: str = "gemini-3.6-flash"
    # Google recommends the default 1.0 for Gemini 3 to avoid degraded reasoning.
    temperature: float = 1.0
    port: int = 8001

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(Path.cwd() / ".env", override=False)
        settings = cls(
            github_mcp_url=os.getenv(
                "GITHUB_MCP_URL", "http://127.0.0.1:8082/"
            ).strip(),
            github_mcp_token=os.getenv("GITHUB_MCP_TOKEN", "").strip(),
            public_base_url=os.getenv(
                "GIT_AGENT_BASE_URL", "http://localhost:8001"
            ).strip(),
            model=os.getenv("GIT_AGENT_MODEL", "gemini-3.6-flash"),
            temperature=float(os.getenv("GIT_AGENT_TEMPERATURE", "1.0")),
            port=int(os.getenv("PORT", "8001")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.github_mcp_url:
            raise ValueError("GITHUB_MCP_URL is required")
        for name, value in (
            ("GITHUB_MCP_URL", self.github_mcp_url),
            ("GIT_AGENT_BASE_URL", self.public_base_url),
        ):
            if value and (
                urlparse(value).scheme not in {"http", "https"}
                or not urlparse(value).netloc
            ):
                raise ValueError(f"{name} must be an HTTP(S) URL")
        if not 1 <= self.port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
        if not 0 <= self.temperature <= 1:
            raise ValueError("GIT_AGENT_TEMPERATURE must be between 0 and 1")
