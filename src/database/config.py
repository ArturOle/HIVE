"""Neo4j configuration using Pydantic Settings.

Environment variables are read with NEO4J_ prefix.
Example: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, etc.

Supports Docker environment detection. When running in Docker compose,
automatically connects to the neo4j service via hostname.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


def _is_docker_environment() -> bool:
    """Detect if running in Docker environment.

    Returns:
        True if running in Docker, False otherwise.
    """
    # Check if /.dockerenv exists (most reliable check)
    if Path("/.dockerenv").exists():
        return True

    # Check DOCKER_CONTAINER env var
    if os.getenv("DOCKER_CONTAINER") == "true":
        return True

    return False


def _get_default_neo4j_uri() -> str:
    """Get default Neo4j URI based on environment.

    In Docker: bolt://neo4j:7687 (service hostname)
    Locally: bolt://localhost:7687

    Returns:
        Default Neo4j connection URI.
    """
    if _is_docker_environment():
        return "bolt://neo4j:7687"
    return "bolt://localhost:7687"


class Neo4jSettings(BaseSettings):
    """Neo4j connection and application settings.

    Settings are loaded from environment variables with NEO4J_ prefix.
    Can be overridden in .env file or directly via constructor.

    Supports Docker environment detection. When running in Docker,
    defaults to connecting to 'neo4j' service host instead of localhost.

    Attributes:
        uri: Neo4j connection URI (bolt, bolt+s, neo4j+s, etc).
        username: Database username.
        password: Database password.
        database: Default database name.
        max_pool_size: Maximum connection pool size.
        connection_timeout_s: Connection timeout in seconds.
        max_retries: Maximum connection retry attempts.
        retry_backoff_ms: Initial retry backoff in milliseconds.
        debug: Enable debug logging.
        docker_enabled: Auto-detect and use Docker Neo4j service if available.
    """

    uri: str = Field(
        default_factory=lambda: _get_default_neo4j_uri(),
        description="Neo4j connection URI",
    )
    username: str = Field(
        default="neo4j",
        description="Neo4j database username",
    )
    password: str = Field(
        default="password",
        description="Neo4j database password",
    )
    database: str = Field(
        default="neo4j",
        description="Default database name to use",
    )

    # Connection pool settings
    max_pool_size: int = Field(
        default=50,
        description="Maximum number of concurrent connections",
    )
    connection_timeout_s: float = Field(
        default=30.0,
        description="Connection timeout in seconds",
    )

    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Maximum connection retry attempts",
    )
    retry_backoff_ms: int = Field(
        default=100,
        description="Initial retry backoff in milliseconds (exponential)",
    )

    # Debug/logging
    debug: bool = Field(
        default=False,
        description="Enable debug logging",
    )
    debug_in_memory: bool = Field(
        default=False,
        description="Enable in-memory debug backend without Neo4j server",
    )

    docker_enabled: bool = Field(
        default_factory=_is_docker_environment,
        description="Auto-detect Docker environment and use neo4j service",
    )

    class Config:
        """Pydantic settings configuration."""

        env_prefix = "NEO4J_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
