"""Database manager - public API for all database operations.

High-level interface that coordinates driver, repository, schema,
and reporting services. Provides convenient methods for agents and orchestrators.

Example:
    >>> from src.database.manager import DatabaseManager
    >>> db = DatabaseManager()
    >>> await db.initialize()
    >>> node = await db.create_node("User", {"name": "Alice"})
    >>> report = await db.get_report()
    >>> await db.close()
"""

from typing import Any, Optional
import logging
import math
import time
import uuid

from src.database.config import Neo4jSettings, load_cypher
from src.database.infrastructure.driver import Neo4jDriver
from src.database.infrastructure.repository import Neo4jRepository
from src.database.infrastructure.schema import SchemaManager
from src.database.infrastructure.reporting import ReportingService

logger = logging.getLogger(__name__)


class DatabaseManager:
    """High-level public API for all database operations.

    Manages and coordinates:
    - Neo4j driver and connection pooling
    - Repository for CRUD and queries
    - Schema setup and management
    - Reporting and diagnostics

    This is the main interface agents and orchestrators should use.

    Example:
        >>> db = DatabaseManager()
        >>> await db.initialize()
        >>> await db.setup_database()  # Setup schema
        >>> node = await db.create_node("User", {"name": "Alice"})
        >>> result = await db.query("MATCH (n) RETURN n LIMIT 10")
        >>> report = await db.get_report()
        >>> await db.close()
    """

    def __init__(self, settings: Optional[Neo4jSettings] = None):
        """Initialize database manager.

        Args:
            settings: Optional Neo4jSettings. If None, loads from environment.
        """
        self.settings = settings or Neo4jSettings()
        self.driver: Optional[Neo4jDriver] = None
        self.repository: Optional[Neo4jRepository] = None
        self.schema: Optional[SchemaManager] = None
        self.reporting: Optional[ReportingService] = None
        self._logger = logger
        self._in_memory = bool(getattr(self.settings, "debug_in_memory", False))
        self._memory_entries: dict[str, dict[str, Any]] = {}
        self._memory_nodes: dict[str, dict[str, dict[str, Any]]] = {
            "Environment": {},
            "Problem": {},
            "Solution": {},
            "Mechanism": {},
            "Result": {},
        }
        self._memory_alternatives: dict[str, set[str]] = {}

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def initialize(self) -> None:
        """Initialize all components and connect to database.

        Establishes connection and sets up repositories.

        Raises:
            RuntimeError: If connection fails after retries.
        """
        self._logger.info("Initializing DatabaseManager")
        if self._in_memory:
            self._logger.warning("DatabaseManager running in in-memory debug mode")
            return

        # Initialize driver
        self.driver = await Neo4jDriver.get_instance(self.settings)
        await self.driver.connect()

        # Initialize repository
        self.repository = Neo4jRepository(self.driver)

        # Initialize schema and reporting
        self.schema = SchemaManager(self.driver)
        self.reporting = ReportingService(self.driver, self.repository)

        self._logger.info("DatabaseManager initialized")

    async def setup_database(self) -> None:
        """Initialize database schema.

        Must call initialize() first. Sets up constraints and indexes.

        Raises:
            RuntimeError: If repository not initialized.
            Exception: If schema setup fails.
        """
        if self._in_memory:
            return
        if not self.schema:
            raise RuntimeError("Must call initialize() first")

        self._logger.info("Setting up database schema")
        await self.schema.setup_schema()

    async def reset_database(self) -> None:
        """Completely reset database to empty state (DESTRUCTIVE).

        Drops all data and recreates schema.
        Useful for testing and development.

        Raises:
            RuntimeError: If schema not initialized.
        """
        if self._in_memory:
            self._memory_entries.clear()
            for nodes in self._memory_nodes.values():
                nodes.clear()
            self._memory_alternatives.clear()
            return
        if not self.schema:
            raise RuntimeError("Must call initialize() first")

        self._logger.warning("Resetting database - all data will be deleted")
        await self.schema.recreate_schema()

    # ===== Node Operations =====

    async def create_node(
        self,
        label: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a node.

        Args:
            label: Node label (e.g., "User", "Document").
            properties: Node properties dictionary.

        Returns:
            Dictionary with id, label, and properties.

        Raises:
            RuntimeError: If repository not initialized.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        return await self.repository.nodes.create_node(label, properties)

    async def get_node(
        self,
        label: str,
        node_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get a node by label and ID.

        Args:
            label: Node label.
            node_id: Element ID.

        Returns:
            Node dictionary or None if not found.

        Raises:
            RuntimeError: If repository not initialized.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        return await self.repository.nodes.read_node(label, node_id)

    async def update_node(
        self,
        label: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a node's properties.

        Args:
            label: Node label.
            node_id: Element ID.
            properties: Properties to merge.

        Returns:
            Updated node dictionary.

        Raises:
            RuntimeError: If repository not initialized or node not found.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        return await self.repository.nodes.update_node(
            label,
            node_id,
            properties,
        )

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
            RuntimeError: If repository not initialized.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        return await self.repository.nodes.delete_node(label, node_id)

    # ===== Relationship Operations =====

    async def create_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a relationship between two nodes.

        Args:
            from_id: Source node element ID.
            rel_type: Relationship type.
            to_id: Target node element ID.
            properties: Optional relationship properties.

        Returns:
            Relationship dictionary.

        Raises:
            RuntimeError: If repository not initialized.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        return await self.repository.relationships.create_relationship(
            from_id,
            rel_type,
            to_id,
            properties,
        )

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
            RuntimeError: If repository not initialized.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        return await self.repository.relationships.delete_relationship(
            from_id,
            rel_type,
            to_id,
        )

    # ===== Query Operations =====

    async def query(
        self,
        cypher: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a custom Cypher query.

        Args:
            cypher: Cypher query string with $param placeholders.
            params: Query parameters dictionary.

        Returns:
            QueryResult with data, count, and execution_time_ms.

        Raises:
            RuntimeError: If repository not initialized.
            Exception: If query is invalid or execution fails.
        """
        if self._in_memory:
            return {"data": [], "count": 0, "execution_time_ms": 0.0}
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        result = await self.repository.nodes.query(cypher, params)
        return {
            "data": result["data"],
            "count": result["count"],
            "execution_time_ms": result["execution_time_ms"],
        }

    async def transaction(
        self,
        operations: list[tuple[str, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Execute multiple operations in a transaction.

        All operations succeed or all fail atomically.

        Args:
            operations: List of (cypher_query, params) tuples.

        Returns:
            List of QueryResult dicts for each operation.

        Raises:
            RuntimeError: If repository not initialized.
            Exception: If any operation fails.
        """
        if not self.repository:
            raise RuntimeError("Must call initialize() first")

        results = await self.repository.transaction(operations)
        return [
            {
                "data": r["data"],
                "count": r["count"],
                "execution_time_ms": r["execution_time_ms"],
            }
            for r in results
        ]

    # ===== Reporting & Diagnostics =====

    async def get_report(self) -> dict[str, Any]:
        """Get comprehensive database report.

        Includes statistics, node overview, and relationship overview.

        Returns:
            Report dictionary.

        Raises:
            RuntimeError: If reporting service not initialized.
        """
        if not self.reporting:
            raise RuntimeError("Must call initialize() first")

        return await self.reporting.generate_full_report()

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics only.

        Returns:
            DatabaseStats dictionary.

        Raises:
            RuntimeError: If reporting service not initialized.
        """
        if not self.reporting:
            raise RuntimeError("Must call initialize() first")

        stats = await self.reporting.get_database_stats()
        return stats.dict()

    # ===== Lifecycle =====

    async def close(self) -> None:
        """Close all connections and cleanup resources.

        Safe to call multiple times.
        """
        if self._in_memory:
            return
        if self.driver:
            await self.driver.close()
            self._logger.info("DatabaseManager closed")

    async def persist_knowledge(
        self,
        extraction: dict[str, str],
        reflection: dict[str, Any],
        embeddings: dict[str, list[float]],
    ) -> dict[str, Any]:
        """Persist structured knowledge for either real or in-memory backend."""
        entry_id = str(uuid.uuid4())
        if self._in_memory:
            concept_map = {
                "environment": "Environment",
                "problem": "Problem",
                "solution": "Solution",
                "mechanism": "Mechanism",
                "result": "Result",
            }
            node_ids: dict[str, str] = {}
            for key, label in concept_map.items():
                text = extraction[key]
                if text not in self._memory_nodes[label]:
                    self._memory_nodes[label][text] = {
                        "id": str(uuid.uuid4()),
                        "text": text,
                        "embedding": embeddings[key],
                        "label": label,
                    }
                node = self._memory_nodes[label][text]
                node["embedding"] = embeddings[key]
                node_ids[key] = node["id"]
                self._memory_alternatives.setdefault(node["id"], set())

            for other in self._memory_entries.values():
                if other["problem"] == extraction["problem"]:
                    self._memory_alternatives[node_ids["solution"]].add(other["solution_node_id"])
                    self._memory_alternatives[node_ids["result"]].add(other["result_node_id"])
                    self._memory_alternatives.setdefault(other["solution_node_id"], set()).add(
                        node_ids["solution"]
                    )
                    self._memory_alternatives.setdefault(other["result_node_id"], set()).add(
                        node_ids["result"]
                    )

            self._memory_entries[entry_id] = {
                "id": entry_id,
                "created_at": time.time(),
                "grade": reflection["grade"],
                "environment": extraction["environment"],
                "problem": extraction["problem"],
                "solution": extraction["solution"],
                "mechanism": extraction["mechanism"],
                "result": extraction["result"],
                "environment_node_id": node_ids["environment"],
                "problem_node_id": node_ids["problem"],
                "solution_node_id": node_ids["solution"],
                "mechanism_node_id": node_ids["mechanism"],
                "result_node_id": node_ids["result"],
            }
            return {"knowledge_entry_id": entry_id}

        query = """
        MERGE (k:KnowledgeEntry {id: $entry_id})
        SET k.created_at = datetime(),
            k.grade = $grade,
            k.reasoning = $reasoning,
            k.key_lesson = $key_lesson,
            k.risk_factors = $risk_factors

        MERGE (env:Environment {text: $environment})
        ON CREATE SET env.created_at = datetime()
        SET env.embedding = $environment_embedding
        MERGE (k)-[:HAS_ENVIRONMENT]->(env)

        MERGE (p:Problem {text: $problem})
        ON CREATE SET p.created_at = datetime()
        SET p.embedding = $problem_embedding
        MERGE (k)-[:HAS_PROBLEM]->(p)

        MERGE (s:Solution {text: $solution})
        ON CREATE SET s.created_at = datetime()
        SET s.embedding = $solution_embedding
        MERGE (k)-[:HAS_SOLUTION]->(s)

        MERGE (m:Mechanism {text: $mechanism})
        ON CREATE SET m.created_at = datetime()
        SET m.embedding = $mechanism_embedding
        MERGE (k)-[:HAS_MECHANISM]->(m)

        MERGE (r:Result {text: $result})
        ON CREATE SET r.created_at = datetime()
        SET r.embedding = $result_embedding
        MERGE (k)-[:HAS_RESULT]->(r)

        MERGE (env)-[:HAS_PROBLEM]->(p)
        MERGE (p)-[:HAS_SOLUTION]->(s)
        MERGE (s)-[:HAS_MECHANISM]->(m)
        MERGE (s)-[:LEADS_TO_RESULT]->(r)
        MERGE (s)-[:WORKS_IN_ENVIRONMENT]->(env)

        WITH k, env, p, s, r
        MATCH (other:KnowledgeEntry)-[:HAS_PROBLEM]->(p)
        WHERE other.id <> k.id
        OPTIONAL MATCH (other)-[:HAS_SOLUTION]->(other_solution:Solution)
        OPTIONAL MATCH (other)-[:HAS_RESULT]->(other_result:Result)
        FOREACH (_ IN CASE WHEN other_solution IS NULL THEN [] ELSE [1] END |
            MERGE (s)-[:ALTERNATIVE_SOLUTION]->(other_solution)
        )
        FOREACH (_ IN CASE WHEN other_result IS NULL THEN [] ELSE [1] END |
            MERGE (r)-[:ALTERNATIVE_RESULT]->(other_result)
        )
        RETURN k.id AS knowledge_entry_id
        """
        params = {
            "entry_id": entry_id,
            "grade": reflection["grade"],
            "reasoning": reflection["reasoning"],
            "key_lesson": reflection["key_lesson"],
            "risk_factors": reflection["risk_factors"],
            "environment": extraction["environment"],
            "problem": extraction["problem"],
            "solution": extraction["solution"],
            "mechanism": extraction["mechanism"],
            "result": extraction["result"],
            "environment_embedding": embeddings["environment"],
            "problem_embedding": embeddings["problem"],
            "solution_embedding": embeddings["solution"],
            "mechanism_embedding": embeddings["mechanism"],
            "result_embedding": embeddings["result"],
        }
        result = await self.query(query, params)
        return result["data"][0] if result["data"] else {"knowledge_entry_id": entry_id}

    async def search_concept_nodes(
        self,
        label: str,
        embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Search concept nodes by vector similarity."""
        
        # cypher = load_cypher()
        if self._in_memory:
            nodes = list(self._memory_nodes.get(label, {}).values())
            ranked = []
            for node in nodes:
                similarity = self._cosine_similarity(embedding, node.get("embedding", []))
                ranked.append(
                    {
                        "node_id": node["id"],
                        "text": node["text"],
                        "embedding": node.get("embedding", []),
                        "similarity": similarity,
                    }
                )
            ranked.sort(key=lambda item: item["similarity"], reverse=True)
            return ranked[:top_k]

        cypher = f"""
        MATCH (n:{label})
        WHERE n.embedding IS NOT NULL
        RETURN elementId(n) AS node_id,
               coalesce(n.text, '') AS text,
               n.embedding AS embedding,
               vector.similarity.cosine(n.embedding, $embedding) AS similarity
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        result = await self.query(cypher, {"embedding": embedding, "top_k": top_k})
        return result["data"]
    
    async def search_concept_nodes_parallel(
        self,
        labels: list[str],
        embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Search concept nodes by vector similarity."""
        cypher = load_cypher("node_exploration/cross_branch")
        if self._in_memory:
            nodes = list(self._memory_nodes.get(label, {}).values())
            ranked = []
            for node in nodes:
                similarity = self._cosine_similarity(embedding, node.get("embedding", []))
                ranked.append(
                    {
                        "node_id": node["id"],
                        "text": node["text"],
                        "embedding": node.get("embedding", []),
                        "similarity": similarity,
                    }
                )
            ranked.sort(key=lambda item: item["similarity"], reverse=True)
            return ranked[:top_k]

        return result["data"]

    async def get_alternative_nodes(
        self,
        node_id: str,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Get alternative connected nodes for a concept node."""
        if self._in_memory:
            reverse_index: dict[str, tuple[str, str]] = {}
            for label, nodes in self._memory_nodes.items():
                for text, node in nodes.items():
                    reverse_index[node["id"]] = (label, text)
            alternatives = []
            for alt_id in list(self._memory_alternatives.get(node_id, set()))[:limit]:
                label, text = reverse_index.get(alt_id, ("Unknown", ""))
                alternatives.append(
                    {"alternative_id": alt_id, "labels": [label], "text": text}
                )
            return alternatives

        cypher = """
        MATCH (n)-[:ALTERNATIVE_SOLUTION|ALTERNATIVE_RESULT|LEADS_TO_RESULT|WORKS_IN_ENVIRONMENT*1..2]-(alt)
        WHERE elementId(n) = $node_id
        RETURN elementId(alt) AS alternative_id,
               labels(alt) AS labels,
               coalesce(alt.text, '') AS text
        LIMIT $limit
        """
        result = await self.query(cypher, {"node_id": node_id, "limit": limit})
        return result["data"]

    async def __aenter__(self) -> "DatabaseManager":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
