"""Neo4j configuration using Pydantic Settings.

Environment variables are read with NEO4J_ prefix.
Example: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, etc.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Neo4jSettings(BaseSettings):
    """Neo4j connection and application settings.

    Settings are loaded from environment variables with NEO4J_ prefix.
    Can be overridden in .env file or directly via constructor.

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
    """

    uri: str = Field(
        default="bolt://localhost:7687",
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

    class Config:
        """Pydantic settings configuration."""

        env_prefix = "NEO4J_"
        env_file = ".env"
        case_sensitive = False
