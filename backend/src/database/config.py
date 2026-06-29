"""Neo4j configuration using Pydantic Settings.

Environment variables are read with NEO4J_ prefix for connection settings.
Example: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_TARGET, etc.

``NEO4J_TARGET`` selects the connection profile:
- ``local`` (default): bolt://localhost:7687 on the host, bolt://neo4j:7687 in Docker
- ``hosted``: Neo4j Aura / remote instance via ``NEO4J_HOSTED_*`` variables
- ``docker``: same as local when on the host; service hostname when inside Compose

Hosted credentials:
- ``NEO4J_HOSTED_URI`` — full URI (optional if ``NEO4J_HOSTED_NAME`` is set)
- ``NEO4J_HOSTED_NAME`` — Aura instance id (builds ``neo4j+s://{id}.databases.neo4j.io``)
- ``NEO4J_HOSTED_USERNAME``, ``NEO4J_HOSTED_PASSWORD``, ``NEO4J_HOSTED_DATABASE``
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Literal, Self

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Neo4jTarget = Literal["local", "hosted", "docker"]

# Project root (ReLived/) — stable .env path regardless of Jupyter cwd
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"
QUERY_DIR = Path(__file__).parent / "cyphers"


class Neo4jTargetMode(str, Enum):
    """Neo4j deployment target."""

    LOCAL = "local"
    HOSTED = "hosted"
    DOCKER = "docker"


def load_project_env(*, override: bool = False) -> Path | None:
    """Load ``.env`` from the project root (safe to call from notebooks).

    Args:
        override: If True, values from ``.env`` replace existing env vars.

    Returns:
        Path to the loaded ``.env`` file, or None if missing.
    """
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=override)
        return _ENV_FILE
    return None

 
def load_cypher(name: str) -> str:
    """Load a .cypher file once at import time, not on every call."""
    return (QUERY_DIR / f"{name}.cypher").read_text()

# Ensure hosted/local credentials from .env are available before Settings loads
load_project_env(override=False)


def _is_docker_environment() -> bool:
    """Detect if running in Docker environment."""
    if Path("/.dockerenv").exists():
        return True
    if os.getenv("DOCKER_CONTAINER") == "true":
        return True
    return False


def _local_uri() -> str:
    """Bolt URI for a Neo4j instance reachable from the current runtime."""
    if _is_docker_environment():
        return "bolt://neo4j:7687"
    return "bolt://localhost:7687"


def _aura_uri_from_instance_id(instance_id: str) -> str:
    """Build a default Neo4j Aura URI from the instance id."""
    instance_id = instance_id.strip()
    if instance_id.startswith(("bolt://", "bolt+s://", "neo4j://", "neo4j+s://")):
        return instance_id
    host = instance_id if ".databases.neo4j.io" in instance_id else f"{instance_id}.databases.neo4j.io"
    return f"neo4j+s://{host}"


def _env_value(name: str) -> str | None:
    """Read and normalize an environment variable (strip quotes/whitespace)."""
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value or None


def _env_value_from_str(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


class Neo4jSettings(BaseSettings):
    """Neo4j connection and application settings."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    target: Neo4jTarget = Field(
        default="local",
        description="Connection profile: local, hosted, or docker",
    )

    uri: str = Field(
        default_factory=_local_uri,
        description="Neo4j connection URI (bolt, bolt+s, neo4j+s, etc)",
    )
    username: str = Field(default="neo4j", description="Neo4j database username")
    password: str = Field(default="password", description="Neo4j database password")
    database: str = Field(default="neo4j", description="Default database name")

    hosted_uri: str | None = Field(
        default=None,
        validation_alias="NEO4J_HOSTED_URI",
        description="Full URI for hosted Neo4j (overrides hosted_name)",
    )
    hosted_name: str | None = Field(
        default=None,
        validation_alias="NEO4J_HOSTED_NAME",
        description="Aura instance id or host fragment",
    )
    hosted_username: str | None = Field(
        default=None,
        validation_alias="NEO4J_HOSTED_USERNAME",
        description="Username for hosted Neo4j (default: neo4j)",
    )
    hosted_password: str | None = Field(
        default=None,
        validation_alias="NEO4J_HOSTED_PASSWORD",
        description="Password for hosted Neo4j",
    )
    hosted_database: str | None = Field(
        default=None,
        validation_alias="NEO4J_HOSTED_DATABASE",
        description="Database name for hosted Neo4j",
    )

    max_pool_size: int = Field(default=50, description="Maximum concurrent connections")
    connection_timeout_s: float = Field(default=30.0, description="Connection timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum connection retry attempts")
    retry_backoff_ms: int = Field(
        default=100,
        description="Initial retry backoff in milliseconds (exponential)",
    )

    debug: bool = Field(default=False, description="Enable debug logging")
    debug_in_memory: bool = Field(
        default=False,
        description="Enable in-memory debug backend without Neo4j server",
    )

    docker_enabled: bool = Field(
        default_factory=_is_docker_environment,
        description="Auto-detect Docker environment",
    )

    @field_validator("target", mode="before")
    @classmethod
    def _normalize_target(cls, value: object) -> str:
        if value is None or value == "":
            return "local"
        return str(value).strip().lower()

    @field_validator("password", "hosted_password", mode="before")
    @classmethod
    def _normalize_secrets(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        return _env_value_from_str(value)

    @model_validator(mode="after")
    def _apply_target_profile(self) -> Self:
        """Resolve uri/credentials from the selected target profile."""
        if self.debug_in_memory:
            return self

        if self.target == Neo4jTargetMode.HOSTED.value:
            self._apply_hosted_profile()
        elif self.target == Neo4jTargetMode.DOCKER.value:
            self.uri = _local_uri()
        elif not _env_value("NEO4J_URI"):
            self.uri = _local_uri()

        return self

    def _hosted_field(self, attr: str, env_name: str) -> str | None:
        """Prefer pydantic-parsed value, then os.environ (notebook / dotenv)."""
        value = getattr(self, attr, None)
        if value:
            return _env_value_from_str(str(value))
        return _env_value(env_name)

    def _apply_hosted_profile(self) -> None:
        hosted_uri = self._hosted_field("hosted_uri", "NEO4J_HOSTED_URI")
        hosted_name = self._hosted_field("hosted_name", "NEO4J_HOSTED_NAME")
        hosted_username = self._hosted_field("hosted_username", "NEO4J_HOSTED_USERNAME")
        hosted_password = self._hosted_field("hosted_password", "NEO4J_HOSTED_PASSWORD")
        hosted_database = self._hosted_field("hosted_database", "NEO4J_HOSTED_DATABASE")

        if hosted_uri:
            self.uri = hosted_uri
        elif hosted_name:
            self.uri = _aura_uri_from_instance_id(hosted_name)
        else:
            raise ValueError(
                "NEO4J_TARGET=hosted requires NEO4J_HOSTED_URI or NEO4J_HOSTED_NAME in .env"
            )

        if hosted_username:
            self.username = hosted_username
        if hosted_password:
            self.password = hosted_password
        elif _env_value("NEO4J_PASSWORD"):
            # Explicit NEO4J_PASSWORD only when no hosted password
            self.password = _env_value("NEO4J_PASSWORD") or self.password
        else:
            raise ValueError(
                "NEO4J_TARGET=hosted requires NEO4J_HOSTED_PASSWORD in .env "
                f"(project root: {_PROJECT_ROOT})"
            )

        if hosted_database:
            self.database = hosted_database

        if self.password in ("", "password"):
            raise ValueError(
                "NEO4J_TARGET=hosted is using the local default password. "
                "Set NEO4J_HOSTED_PASSWORD in .env (Aura console → Reset password)."
            )

    @classmethod
    def for_target(cls, target: Neo4jTarget | Neo4jTargetMode | str) -> "Neo4jSettings":
        """Load settings for a specific target (local, hosted, docker)."""
        load_project_env(override=False)
        if isinstance(target, Neo4jTargetMode):
            target = target.value
        return cls(target=str(target).strip().lower())

    def credentials_ok_for_hosted(self) -> bool:
        """True if hosted password appears configured (for diagnostics)."""
        if self.target != Neo4jTargetMode.HOSTED.value:
            return True
        return bool(self.hosted_password or _env_value("NEO4J_HOSTED_PASSWORD")) and (
            self.password not in ("", "password")
        )

    def connection_summary(self) -> str:
        """Human-readable connection label (no secrets)."""
        if self.debug_in_memory:
            return "in-memory (debug)"
        scheme = self.uri.split("://", 1)[0] if "://" in self.uri else "bolt"
        host = self.uri.split("://", 1)[-1].split("@")[-1]
        cred = "ok" if self.credentials_ok_for_hosted() else "MISSING hosted password"
        return (
            f"{self.target} ({scheme}://…{host}, db={self.database}, "
            f"user={self.username}, creds={cred})"
        )

 