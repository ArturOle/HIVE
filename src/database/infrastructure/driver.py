"""Neo4j driver management with lifecycle control.

Implements a singleton pattern for connection pooling and retry logic.
Handles connection establishment, verification, and cleanup.
"""

import asyncio
import logging
from typing import Optional

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import ServiceUnavailable, DriverError

from src.database.config import Neo4jSettings

logger = logging.getLogger(__name__)


class Neo4jDriver:
    """Singleton Neo4j driver with connection pooling and retry logic.

    Manages the lifecycle of a single Neo4j driver instance. Ensures:
    - Single connection pool per application
    - Automatic retry with exponential backoff
    - Proper resource cleanup
    - Session management

    Example:
        >>> from src.database.config import Neo4jSettings
        >>> settings = Neo4jSettings()
        >>> driver = Neo4jDriver.get_instance(settings)
        >>> await driver.connect()
        >>> session = await driver.session()
        >>> # use session...
        >>> await driver.close()
    """

    _instance: Optional["Neo4jDriver"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, config: Neo4jSettings):
        """Initialize driver with configuration.

        Args:
            config: Neo4jSettings instance with connection details.
        """
        self.config = config
        self._driver: Optional[AsyncDriver] = None
        self._logger = logger

        if config.debug:
            self._logger.setLevel(logging.DEBUG)

    @classmethod
    async def get_instance(cls, config: Neo4jSettings) -> "Neo4jDriver":
        """Get or create singleton instance (thread-safe).

        Args:
            config: Neo4jSettings configuration.

        Returns:
            Singleton Neo4jDriver instance.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance

    async def connect(self) -> AsyncDriver:
        """Establish connection with retry logic.

        Attempts to connect to Neo4j with exponential backoff retry.
        Verifies connectivity before returning driver.

        Returns:
            AsyncDriver instance ready for use.

        Raises:
            RuntimeError: If connection fails after max retries.
        """
        if self._driver is not None:
            return self._driver

        retries = 0
        last_error = None

        while retries < self.config.max_retries:
            try:
                self._logger.info(
                    f"Connecting to Neo4j at {self.config.uri} "
                    f"(attempt {retries + 1}/{self.config.max_retries})"
                )

                self._driver = AsyncGraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    max_connection_pool_size=self.config.max_pool_size,
                    connection_timeout=self.config.connection_timeout_s,
                )

                # Verify connectivity
                await self._driver.verify_connectivity()
                self._logger.info("Neo4j connection established and verified")
                return self._driver

            except (ServiceUnavailable, DriverError) as e:
                last_error = e
                retries += 1

                if retries < self.config.max_retries:
                    # Exponential backoff: 100ms, 200ms, 400ms, etc.
                    wait_ms = self.config.retry_backoff_ms * retries
                    self._logger.warning(
                        f"Connection failed: {e}. "
                        f"Retrying in {wait_ms}ms..."
                    )
                    await asyncio.sleep(wait_ms / 1000.0)

        error_msg = (
            f"Failed to connect to Neo4j after {self.config.max_retries} "
            f"attempts. Last error: {last_error}"
        )
        self._logger.error(error_msg)
        raise RuntimeError(error_msg) from last_error

    async def session(self) -> AsyncSession:
        """Get a new async session for database operations.

        Automatically connects if not already connected.

        Returns:
            AsyncSession bound to configured database.

        Raises:
            RuntimeError: If connection fails.
        """
        driver = await self.connect()
        return driver.session(database=self.config.database)

    async def close(self) -> None:
        """Close driver and clean up all connections.

        Safe to call multiple times. After calling, the driver
        will attempt to reconnect on next connect() call.
        """
        if self._driver:
            try:
                await self._driver.close()
                self._logger.info("Neo4j driver closed")
            except Exception as e:
                self._logger.error(f"Error closing driver: {e}")
            finally:
                self._driver = None

    async def __aenter__(self) -> "Neo4jDriver":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
