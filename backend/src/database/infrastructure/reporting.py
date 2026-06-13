"""Reporting and diagnostics for database overview and statistics.

Generate comprehensive database reports, statistics, and health diagnostics.
"""

import logging
from datetime import datetime
from typing import Any

from src.database.domain.models import DatabaseStats
from src.database.infrastructure.driver import Neo4jDriver
from src.database.infrastructure.repository import Neo4jRepository

logger = logging.getLogger(__name__)


class ReportingService:
    """Generate database overview and diagnostics.

    Provides statistical summaries, node/relationship distribution,
    and comprehensive reports about database state.

    Example:
        >>> driver = await Neo4jDriver.get_instance(config)
        >>> repo = Neo4jRepository(driver)
        >>> reporting = ReportingService(driver, repo)
        >>> stats = await reporting.get_database_stats()
        >>> report = await reporting.generate_full_report()
    """

    def __init__(self, driver: Neo4jDriver, repository: Neo4jRepository):
        """Initialize reporting service.

        Args:
            driver: Neo4jDriver instance.
            repository: Neo4jRepository instance for queries.
        """
        self.driver = driver
        self.repository = repository
        self._logger = logger

    async def get_database_stats(self) -> DatabaseStats:
        """Get comprehensive database statistics.

        Calculates node counts, relationship counts, and distribution.

        Returns:
            DatabaseStats with node and relationship counts.

        Raises:
            Exception: If query fails.
        """
        session = await self.driver.session()
        try:
            # Get node and relationship counts
            counts = await session.run(
                """
                CALL apoc.meta.stats()
                YIELD nodeCount, relCount
                RETURN nodeCount, relCount
                """
            )
            counts_record = await counts.single()

            # Get node counts by label
            labels = await session.run(
                """
                CALL apoc.meta.stats()
                YIELD labels
                UNWIND labels as label
                RETURN label, label.count as count
                """
            )
            labels_records = await labels.fetch(None)

            # Get relationship counts by type
            rels = await session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
                """
            )
            rels_records = await rels.fetch(None)

            return DatabaseStats(
                total_nodes=counts_record["nodeCount"] if counts_record else 0,
                total_relationships=counts_record["relCount"]
                if counts_record
                else 0,
                node_count_by_label={
                    r["label"]: r["count"]
                    for r in labels_records
                    if r and r["label"]
                },
                relationship_count_by_type={
                    r["rel_type"]: r["count"]
                    for r in rels_records
                    if r and r["rel_type"]
                },
            )

        except Exception as e:
            self._logger.error(f"Failed to get database stats: {e}")
            # Return empty stats on error
            return DatabaseStats(
                total_nodes=0,
                total_relationships=0,
                node_count_by_label={},
                relationship_count_by_type={},
            )
        finally:
            await session.close()

    async def get_node_overview(self) -> dict[str, Any]:
        """Get overview of all node labels and their counts.

        Returns:
            Dictionary with node label statistics.

        Raises:
            Exception: If query fails.
        """
        try:
            result = await self.repository.nodes.query(
                """
                CALL db.labels() YIELD label
                CALL {
                    WITH label
                    MATCH (n)
                    WHERE any(lbl in labels(n) WHERE lbl = label)
                    RETURN count(n) as cnt
                }
                RETURN label, cnt as count
                ORDER BY count DESC
                """
            )
            return {
                "timestamp": datetime.now().isoformat(),
                "labels": [
                    {"label": r["label"], "count": r["count"]}
                    for r in result.data
                ],
            }
        except Exception as e:
            self._logger.error(f"Failed to get node overview: {e}")
            return {"timestamp": datetime.now().isoformat(), "labels": []}

    async def get_relationship_overview(self) -> dict[str, Any]:
        """Get overview of all relationship types and their counts.

        Returns:
            Dictionary with relationship type statistics.

        Raises:
            Exception: If query fails.
        """
        try:
            result = await self.repository.nodes.query(
                """
                CALL db.relationshipTypes() YIELD relationshipType
                CALL {
                    WITH relationshipType
                    MATCH ()-[r]->()
                    WHERE type(r) = relationshipType
                    RETURN count(r) as cnt
                }
                RETURN relationshipType, cnt as count
                ORDER BY count DESC
                """
            )
            return {
                "timestamp": datetime.now().isoformat(),
                "types": [
                    {
                        "type": r["relationshipType"],
                        "count": r["count"],
                    }
                    for r in result.data
                ],
            }
        except Exception as e:
            self._logger.error(f"Failed to get relationship overview: {e}")
            return {"timestamp": datetime.now().isoformat(), "types": []}

    async def generate_full_report(self) -> dict[str, Any]:
        """Generate comprehensive database report.

        Includes statistics, node overview, and relationship overview.

        Returns:
            Complete database report dictionary.
        """
        stats = await self.get_database_stats()
        nodes = await self.get_node_overview()
        rels = await self.get_relationship_overview()

        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats.dict(),
            "nodes": nodes,
            "relationships": rels,
        }
