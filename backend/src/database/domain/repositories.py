"""Abstract repository protocols for Neo4j operations.

Defines contracts (Protocols) that concrete implementations must satisfy.
This enables clean architecture and testability through dependency inversion.
"""

from typing import Protocol, Any, runtime_checkable
from .models import QueryResult


@runtime_checkable
class NodeRepository(Protocol):
    """Abstract interface for node (vertex) operations.

    Any class implementing this protocol can be used interchangeably,
    enabling mock implementations for testing.
    """

    async def create_node(
        self,
        label: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a node with given label and properties.

        Args:
            label: Node label (e.g., "User", "Document").
            properties: Dictionary of node properties.

        Returns:
            Dictionary with id, label, and all properties.

        Raises:
            Exception: If node creation fails.
        """
        ...

    async def read_node(
        self,
        label: str,
        node_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a node by label and element ID.

        Args:
            label: Node label to match.
            node_id: Node's element ID.

        Returns:
            Dictionary with id, label, and properties, or None if not found.
        """
        ...

    async def update_node(
        self,
        label: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update node properties.

        Args:
            label: Node label.
            node_id: Node's element ID.
            properties: Properties to merge (MERGE semantics).

        Returns:
            Updated node dictionary.

        Raises:
            Exception: If node not found or update fails.
        """
        ...

    async def delete_node(
        self,
        label: str,
        node_id: str,
    ) -> bool:
        """Delete a node.

        Args:
            label: Node label.
            node_id: Node's element ID.

        Returns:
            True if deleted, False if not found.

        Raises:
            Exception: If deletion fails due to constraints.
        """
        ...

    async def query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute a custom Cypher query.

        Args:
            cypher: Cypher query string with $param placeholders.
            params: Query parameters dict.

        Returns:
            QueryResult with data, count, and execution_time_ms.

        Raises:
            Exception: If query is invalid or execution fails.
        """
        ...


@runtime_checkable
class RelationshipRepository(Protocol):
    """Abstract interface for relationship operations."""

    async def create_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a directed relationship between two nodes.

        Args:
            from_id: Source node element ID.
            rel_type: Relationship type (e.g., "REFERENCES", "DEPENDS_ON").
            to_id: Target node element ID.
            properties: Optional relationship properties.

        Returns:
            Dictionary with id, from_id, to_id, rel_type, and properties.

        Raises:
            Exception: If nodes don't exist or creation fails.
        """
        ...

    async def delete_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
    ) -> bool:
        """Delete a directed relationship.

        Args:
            from_id: Source node element ID.
            rel_type: Relationship type.
            to_id: Target node element ID.

        Returns:
            True if deleted, False if not found.

        Raises:
            Exception: If deletion fails.
        """
        ...


@runtime_checkable
class DatabaseRepository(Protocol):
    """Combined protocol for all database operations.

    Provides high-level interface for agents and orchestrators.
    """

    # Composition of sub-repositories
    nodes: NodeRepository
    relationships: RelationshipRepository

    async def transaction(
        self,
        operations: list[tuple[str, dict[str, Any]]],
    ) -> list[QueryResult]:
        """Execute multiple operations within a transaction.

        All operations succeed or all fail atomically.

        Args:
            operations: List of (cypher_query, params) tuples.

        Returns:
            List of QueryResult for each operation, in order.

        Raises:
            Exception: If any operation fails (entire transaction rolled back).
        """
        ...

    async def close(self) -> None:
        """Close repository and release resources.

        After calling this, the repository should not be used.
        """
        ...
