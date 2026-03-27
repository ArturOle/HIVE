"""Domain models for Neo4j graph entities."""

from typing import Any, TypedDict, Optional
from pydantic import BaseModel
from datetime import datetime


class QueryResult(TypedDict):
    """Standard result format from Cypher queries.

    Attributes:
        data: List of result records (each as dict).
        count: Number of records returned.
        execution_time_ms: Query execution time in milliseconds.
    """

    data: list[dict[str, Any]]
    count: int
    execution_time_ms: float


class Node(BaseModel):
    """Represents a graph node.

    Attributes:
        id: Unique element ID in Neo4j.
        label: Node label(s).
        properties: Node properties dictionary.
        created_at: Creation timestamp.
    """

    id: str
    label: str
    properties: dict[str, Any]
    created_at: Optional[datetime] = None

    class Config:
        """Pydantic config for Node model."""

        frozen = True


class Relationship(BaseModel):
    """Represents a directed relationship between nodes.

    Attributes:
        id: Unique element ID in Neo4j.
        from_id: Source node element ID.
        to_id: Target node element ID.
        rel_type: Relationship type.
        properties: Relationship properties dictionary.
    """

    id: str
    from_id: str
    to_id: str
    rel_type: str
    properties: Optional[dict[str, Any]] = None

    class Config:
        """Pydantic config for Relationship model."""

        frozen = True


class DatabaseStats(BaseModel):
    """Database overview statistics.

    Attributes:
        total_nodes: Total number of nodes in database.
        total_relationships: Total number of relationships.
        node_count_by_label: Count of nodes grouped by label.
        relationship_count_by_type: Count of relationships by type.
        database_size_bytes: Database size in bytes (optional).
    """

    total_nodes: int
    total_relationships: int
    node_count_by_label: dict[str, int]
    relationship_count_by_type: dict[str, int]
    database_size_bytes: Optional[int] = None

    class Config:
        """Pydantic config for DatabaseStats model."""

        frozen = True
