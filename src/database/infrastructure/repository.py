"""Neo4j repository implementation with CRUD and query abstraction.

Concrete implementation of domain repository protocols.
Abstracts Cypher queries and handles session lifecycle.
"""

import time
import logging
from typing import Any

from neo4j import AsyncSession

from src.database.domain.models import QueryResult
from src.database.domain.repositories import (
    NodeRepository,
    RelationshipRepository,
)
from src.database.infrastructure.driver import Neo4jDriver

logger = logging.getLogger(__name__)


class Neo4jRepository:
    """Concrete Neo4j repository implementation.

    Provides CRUD operations and query abstraction for Neo4j.
    Uses composition to organize node and relationship operations.

    Example:
        >>> driver = await Neo4jDriver.get_instance(config)
        >>> repo = Neo4jRepository(driver)
        >>> node = await repo.nodes.create_node("User", {"name": "Alice"})
        >>> result = await repo.nodes.query("MATCH (n) RETURN n")
        >>> await repo.close()
    """

    def __init__(self, driver: Neo4jDriver):
        """Initialize repository.

        Args:
            driver: Neo4jDriver instance.
        """
        self.driver = driver
        self.nodes = self._NodeRepository(driver)
        self.relationships = self._RelationshipRepository(driver)
        self._logger = logger

    class _NodeRepository(NodeRepository):
        """Concrete node repository operations."""

        def __init__(self, driver: Neo4jDriver):
            self.driver = driver
            self._logger = logger

        async def create_node(
            self,
            label: str,
            properties: dict[str, Any],
        ) -> dict[str, Any]:
            """Create a node with given label and properties.

            Args:
                label: Node label.
                properties: Node properties dictionary.

            Returns:
                Dictionary with id, label, and properties.

            Raises:
                Exception: If creation fails.
            """
            query = f"""
            CREATE (n:{label})
            SET n += $props
            RETURN elementId(n) as id, properties(n) as props
            """

            session = await self.driver.session()
            try:
                result = await session.run(query, props=properties)
                record = await result.single()

                if not record:
                    raise RuntimeError(f"Failed to create node with label {label}")

                return {
                    "id": record["id"],
                    "label": label,
                    **record["props"],
                }
            finally:
                await session.close()

        async def read_node(
            self,
            label: str,
            node_id: str,
        ) -> dict[str, Any] | None:
            """Retrieve a node by label and element ID.

            Args:
                label: Node label.
                node_id: Element ID.

            Returns:
                Node dict or None if not found.
            """
            query = f"""
            MATCH (n:{label})
            WHERE elementId(n) = $id
            RETURN elementId(n) as id, properties(n) as props
            """

            session = await self.driver.session()
            try:
                result = await session.run(query, id=node_id)
                record = await result.single()

                if record:
                    return {
                        "id": record["id"],
                        "label": label,
                        **record["props"],
                    }
                return None
            finally:
                await session.close()

        async def update_node(
            self,
            label: str,
            node_id: str,
            properties: dict[str, Any],
        ) -> dict[str, Any]:
            """Update node properties.

            Uses SET semantics to merge properties.

            Args:
                label: Node label.
                node_id: Element ID.
                properties: Properties to merge.

            Returns:
                Updated node dict.

            Raises:
                Exception: If node not found or update fails.
            """
            query = f"""
            MATCH (n:{label})
            WHERE elementId(n) = $id
            SET n += $props
            RETURN elementId(n) as id, properties(n) as props
            """

            session = await self.driver.session()
            try:
                result = await session.run(query, id=node_id, props=properties)
                record = await result.single()

                if not record:
                    raise RuntimeError(
                        f"Node with label {label} and id {node_id} not found"
                    )

                return {
                    "id": record["id"],
                    "label": label,
                    **record["props"],
                }
            finally:
                await session.close()

        async def delete_node(
            self,
            label: str,
            node_id: str,
        ) -> bool:
            """Delete a node.

            Args:
                label: Node label.
                node_id: Element ID.

            Returns:
                True if deleted, False if not found.

            Raises:
                Exception: If deletion fails (e.g., constraint violation).
            """
            query = f"""
            MATCH (n:{label})
            WHERE elementId(n) = $id
            DELETE n
            RETURN true
            """

            session = await self.driver.session()
            try:
                result = await session.run(query, id=node_id)
                record = await result.single()
                return record is not None
            finally:
                await session.close()

        async def query(
            self,
            cypher: str,
            params: dict[str, Any] | None = None,
        ) -> QueryResult:
            """Execute a custom Cypher query.

            Args:
                cypher: Cypher query string with $param placeholders.
                params: Parameter dictionary.

            Returns:
                QueryResult with data, count, and execution time.

            Raises:
                Exception: If query is invalid or execution fails.
            """
            session = await self.driver.session()
            try:
                start = time.time()
                result = await session.run(cypher, params or {})
                records = await result.fetch(None)  # Fetch all
                elapsed_ms = (time.time() - start) * 1000.0

                return QueryResult(
                    data=[dict(r) for r in records],
                    count=len(records),
                    execution_time_ms=elapsed_ms,
                )
            except Exception as e:
                self._logger.error(f"Query failed: {e}\nCypher: {cypher}")
                raise
            finally:
                await session.close()

    class _RelationshipRepository(RelationshipRepository):
        """Concrete relationship repository operations."""

        def __init__(self, driver: Neo4jDriver):
            self.driver = driver
            self._logger = logger

        async def create_relationship(
            self,
            from_id: str,
            rel_type: str,
            to_id: str,
            properties: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            """Create a relationship between two nodes.

            Args:
                from_id: Source node element ID.
                rel_type: Relationship type.
                to_id: Target node element ID.
                properties: Optional relationship properties.

            Returns:
                Relationship dict with id, from_id, to_id, rel_type, properties.

            Raises:
                Exception: If nodes don't exist or creation fails.
            """
            query = f"""
            MATCH (from) WHERE elementId(from) = $from_id
            MATCH (to) WHERE elementId(to) = $to_id
            CREATE (from)-[r:{rel_type}]->(to)
            SET r += $props
            RETURN elementId(r) as id, type(r) as rel_type, 
                   properties(r) as props
            """

            session = await self.driver.session()
            try:
                result = await session.run(
                    query,
                    from_id=from_id,
                    to_id=to_id,
                    props=properties or {},
                )
                record = await result.single()

                if not record:
                    raise RuntimeError(
                        f"Failed to create relationship {rel_type} from "
                        f"{from_id} to {to_id}"
                    )

                return {
                    "id": record["id"],
                    "from_id": from_id,
                    "to_id": to_id,
                    "rel_type": record["rel_type"],
                    **(record["props"] or {}),
                }
            finally:
                await session.close()

        async def delete_relationship(
            self,
            from_id: str,
            rel_type: str,
            to_id: str,
        ) -> bool:
            """Delete a relationship.

            Args:
                from_id: Source node element ID.
                rel_type: Relationship type.
                to_id: Target node element ID.

            Returns:
                True if deleted, False if not found.

            Raises:
                Exception: If deletion fails.
            """
            query = f"""
            MATCH (from)-[r:{rel_type}]->(to)
            WHERE elementId(from) = $from_id AND elementId(to) = $to_id
            DELETE r
            RETURN true
            """

            session = await self.driver.session()
            try:
                result = await session.run(query, from_id=from_id, to_id=to_id)
                record = await result.single()
                return record is not None
            finally:
                await session.close()

    async def transaction(
        self,
        operations: list[tuple[str, dict[str, Any]]],
    ) -> list[QueryResult]:
        """Execute multiple operations within a transaction.

        All operations succeed or all fail atomically.

        Args:
            operations: List of (cypher_query, params) tuples.

        Returns:
            List of QueryResult for each operation in order.

        Raises:
            Exception: If any operation fails (entire transaction rolled back).
        """
        session = await self.driver.session()
        try:
            async with session.begin_transaction() as tx:
                results = []
                for cypher, params in operations:
                    start = time.time()
                    result = await tx.run(cypher, params)
                    records = await result.fetch(None)
                    elapsed_ms = (time.time() - start) * 1000.0

                    results.append(
                        QueryResult(
                            data=[dict(r) for r in records],
                            count=len(records),
                            execution_time_ms=elapsed_ms,
                        )
                    )
                return results
        finally:
            await session.close()

    async def close(self) -> None:
        """Close repository and release resources."""
        await self.driver.close()
