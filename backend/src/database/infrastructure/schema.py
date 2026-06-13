"""Schema management: initialization, constraints, indexes, and reset.

Handles database schema setup, constraint creation, index creation,
and destructive operations like drop and recreate.
"""

import logging

from src.database.infrastructure.driver import Neo4jDriver

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manage database schema including indexes and constraints.

    Example:
        >>> driver = await Neo4jDriver.get_instance(config)
        >>> schema = SchemaManager(driver)
        >>> await schema.setup_schema()
    """

    def __init__(self, driver: Neo4jDriver):
        """Initialize schema manager.

        Args:
            driver: Neo4jDriver instance.
        """
        self.driver = driver
        self._logger = logger

    async def setup_schema(self) -> None:
        """Initialize schema with constraints and indexes.

        Creates standard constraints and indexes.
        Safe to run multiple times (uses IF NOT EXISTS).

        Raises:
            Exception: If schema setup fails.
        """
        session = await self.driver.session()
        try:
            # Define constraints - enforce data integrity
            constraints = [
                "CREATE CONSTRAINT node_id_unique IF NOT EXISTS "
                "FOR (n:Node) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT document_id_unique IF NOT EXISTS "
                "FOR (d:Document) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT knowledge_entry_id_unique IF NOT EXISTS "
                "FOR (k:KnowledgeEntry) REQUIRE k.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    await session.run(constraint)
                    self._logger.info("Applied constraint")
                except Exception as e:
                    self._logger.warning(f"Constraint creation: {e}")

            # Define indexes - improve query performance
            indexes = [
                "CREATE INDEX node_created_at IF NOT EXISTS "
                "FOR (n:Node) ON (n.created_at)",
                "CREATE INDEX document_status IF NOT EXISTS "
                "FOR (d:Document) ON (d.status)",
                "CREATE INDEX environment_text IF NOT EXISTS "
                "FOR (n:Environment) ON (n.text)",
                "CREATE INDEX problem_text IF NOT EXISTS "
                "FOR (n:Problem) ON (n.text)",
                "CREATE INDEX solution_text IF NOT EXISTS "
                "FOR (n:Solution) ON (n.text)",
                "CREATE INDEX mechanism_text IF NOT EXISTS "
                "FOR (n:Mechanism) ON (n.text)",
                "CREATE INDEX result_text IF NOT EXISTS "
                "FOR (n:Result) ON (n.text)",
                "CREATE VECTOR INDEX environment_embedding IF NOT EXISTS "
                "FOR (n:Environment) ON (n.embedding) "
                "OPTIONS {indexConfig: {`vector.dimensions`: 32, "
                "`vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX problem_embedding IF NOT EXISTS "
                "FOR (n:Problem) ON (n.embedding) "
                "OPTIONS {indexConfig: {`vector.dimensions`: 32, "
                "`vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX solution_embedding IF NOT EXISTS "
                "FOR (n:Solution) ON (n.embedding) "
                "OPTIONS {indexConfig: {`vector.dimensions`: 32, "
                "`vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX mechanism_embedding IF NOT EXISTS "
                "FOR (n:Mechanism) ON (n.embedding) "
                "OPTIONS {indexConfig: {`vector.dimensions`: 32, "
                "`vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX result_embedding IF NOT EXISTS "
                "FOR (n:Result) ON (n.embedding) "
                "OPTIONS {indexConfig: {`vector.dimensions`: 32, "
                "`vector.similarity_function`: 'cosine'}}",
            ]

            for index in indexes:
                try:
                    await session.run(index)
                    self._logger.info("Applied index")
                except Exception as e:
                    self._logger.warning(f"Index creation: {e}")

            self._logger.info("Schema setup complete")

        finally:
            await session.close()

    async def drop_all(self, confirm: bool = False) -> None:
        """Drop all nodes and relationships (DESTRUCTIVE).

        This permanently deletes all data in the database.
        Must explicitly confirm with confirm=True to prevent accidents.

        Args:
            confirm: Must be True to proceed.

        Raises:
            ValueError: If confirm is not True.
            Exception: If delete operation fails.
        """
        if not confirm:
            raise ValueError(
                "Destructive operation blocked. Must confirm with confirm=True"
            )

        session = await self.driver.session()
        try:
            await session.run("MATCH (n) DETACH DELETE n")
            self._logger.warning("All nodes and relationships deleted")
        finally:
            await session.close()

    async def recreate_schema(self) -> None:
        """Drop all data and recreate schema (DESTRUCTIVE).

        Useful for testing and development to start fresh.
        Deletes all nodes, relationships, then re-initializes schema.

        Raises:
            Exception: If operations fail.
        """
        self._logger.warning("Recreating schema - dropping all data")
        await self.drop_all(confirm=True)
        await self.setup_schema()
        self._logger.info("Schema recreated")

    async def reset_to_empty_graph(self) -> None:
        """Reset database to completely empty graph.

        Alias for drop_all with convenience method.

        Raises:
            Exception: If delete fails.
        """
        await self.drop_all(confirm=True)
