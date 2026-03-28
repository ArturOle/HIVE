"""Database module - Neo4j management and repository pattern.

Provides clean architecture for database operations with:
- Domain layer: protocols and models
- Infrastructure layer: driver, repository, schema, reporting
- Public API: DatabaseManager for high-level operations

Main entry point: DatabaseManager
"""

from .manager import DatabaseManager
from .config import Neo4jSettings
from .domain import (
    Node,
    Relationship,
    DatabaseStats,
    QueryResult,
    NodeRepository,
    RelationshipRepository,
    DatabaseRepository,
)

__all__ = [
    "DatabaseManager",
    "Neo4jSettings",
    # Domain
    "Node",
    "Relationship",
    "DatabaseStats",
    "QueryResult",
    "NodeRepository",
    "RelationshipRepository",
    "DatabaseRepository",
]
