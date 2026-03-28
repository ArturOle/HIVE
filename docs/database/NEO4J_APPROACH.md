# Neo4j Management System - Proposed Approach

## 1. Architecture Overview

### Layered Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    AI/LangGraph Layer                        │
│         (src/ai/ agents use database operations)             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Orchestrator (Logic Layer)                 │
│         (src/logic/orchestrate.py - dependency injection)    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Application Layer (Public API)                  │
│         (src/database/manager.py - high-level interface)     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Domain Layer                              │
│  ├─ Protocols (abstract repositories)                       │
│  └─ Models (TypedDict, Pydantic dataclasses)               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                Infrastructure Layer                          │
│  ├─ Neo4j Driver Management (connection pooling)            │
│  ├─ Repository Implementation (Cypher queries)              │
│  ├─ Schema Management (init, constraints, indexes)          │
│  ├─ Reporting (diagnostics, overview)                       │
│  └─ Configuration (Pydantic Settings)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                    Neo4j Database
```

---

## 2. Directory Structure

```
src/database/
├── __init__.py                          # Public exports
├── manager.py                           # Application layer (existing)
├── config.py                            # Environment configuration
│
├── domain/
│   ├── __init__.py
│   ├── models.py                        # Pydantic models, TypedDict
│   └── repositories.py                  # Abstract Protocol interfaces
│
└── infrastructure/
    ├── __init__.py
    ├── driver.py                        # Neo4j driver singleton
    ├── repository.py                    # Neo4jRepository implementation
    ├── schema.py                        # Schema setup, constraints, indexes
    ├── reporting.py                     # Database overview, diagnostics
    └── queries.py                       # Centralized Cypher queries
```

---

## 3. Core Patterns & Interfaces

### 3.1 Domain Layer - Protocols (Abstract Interfaces)

**Purpose:** Define contracts for database operations. This enables:
- Testing without a real Neo4j instance (mock implementations)
- Clean separation of concerns
- Flexibility to swap implementations later

```python
# src/database/domain/repositories.py
from typing import Protocol, Any
from typing_extensions import TypedDict

class QueryResult(TypedDict):
    """Standard result format from queries."""
    data: list[dict[str, Any]]
    count: int
    execution_time_ms: float

class NodeRepository(Protocol):
    """Abstract interface for node operations."""
    
    async def create_node(
        self,
        label: str,
        properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a node and return it with ID."""
        ...
    
    async def read_node(
        self,
        label: str,
        node_id: str
    ) -> dict[str, Any] | None:
        """Retrieve a node by ID."""
        ...
    
    async def update_node(
        self,
        label: str,
        node_id: str,
        properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Update node properties."""
        ...
    
    async def delete_node(
        self,
        label: str,
        node_id: str
    ) -> bool:
        """Delete a node."""
        ...
    
    async def query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None
    ) -> QueryResult:
        """Execute custom Cypher query."""
        ...

class RelationshipRepository(Protocol):
    """Abstract interface for relationship operations."""
    
    async def create_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a relationship."""
        ...
    
    async def delete_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str
    ) -> bool:
        """Delete a relationship."""
        ...

class DatabaseRepository(Protocol):
    """Combined interface for all database operations."""
    
    # Composition
    nodes: NodeRepository
    relationships: RelationshipRepository
    
    async def transaction(
        self,
        operations: list[tuple[str, dict]]
    ) -> list[QueryResult]:
        """Execute multiple operations in a transaction."""
        ...
    
    async def close(self) -> None:
        """Close database connection."""
        ...
```

### 3.2 Domain Layer - Models

```python
# src/database/domain/models.py
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

class Node(BaseModel):
    """Represents a graph node."""
    id: str
    label: str
    properties: dict[str, Any]
    created_at: datetime | None = None
    
    class Config:
        frozen = True

class Relationship(BaseModel):
    """Represents a graph relationship."""
    id: str
    from_id: str
    to_id: str
    rel_type: str
    properties: dict[str, Any] | None = None
    
    class Config:
        frozen = True

class DatabaseStats(BaseModel):
    """Database overview statistics."""
    total_nodes: int
    total_relationships: int
    node_count_by_label: dict[str, int]
    relationship_count_by_type: dict[str, int]
    database_size_bytes: int | None = None
```

---

## 4. Infrastructure Layer - Key Components

### 4.1 Configuration (Pydantic Settings)

```python
# src/database/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Neo4jSettings(BaseSettings):
    """Neo4j connection and application settings."""
    
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    username: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    password: str = Field(
        default="password",
        description="Neo4j password"
    )
    database: str = Field(
        default="neo4j",
        description="Default database name"
    )
    
    # Connection pool settings
    max_pool_size: int = Field(
        default=50,
        description="Maximum connection pool size"
    )
    connection_timeout_s: float = Field(
        default=30.0,
        description="Connection timeout in seconds"
    )
    
    # Retry settings
    max_retries: int = Field(default=3)
    retry_backoff_ms: int = Field(default=100)
    
    # Debug/logging
    debug: bool = Field(default=False)
    
    class Config:
        env_prefix = "NEO4J_"
        env_file = ".env"
        case_sensitive = False
```

### 4.2 Driver Management

```python
# src/database/infrastructure/driver.py
import logging
from typing import Optional
from neo4j import AsyncDriver, AsyncSession, auth
from neo4j.exceptions import ServiceUnavailable, DriverError

logger = logging.getLogger(__name__)

class Neo4jDriver:
    """Singleton driver management with lifecycle control."""
    
    _instance: Optional['Neo4jDriver'] = None
    
    def __init__(self, config: Neo4jSettings):
        self.config = config
        self._driver: Optional[AsyncDriver] = None
        self._session: Optional[AsyncSession] = None
    
    @classmethod
    def get_instance(cls, config: Neo4jSettings) -> 'Neo4jDriver':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    async def connect(self) -> AsyncDriver:
        """Establish connection with retry logic."""
        if self._driver is not None:
            return self._driver
        
        retries = 0
        last_error = None
        
        while retries < self.config.max_retries:
            try:
                self._driver = AsyncDriver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    max_pool_size=self.config.max_pool_size,
                    connection_timeout=self.config.connection_timeout_s,
                )
                await self._driver.verify_connectivity()
                logger.info("Neo4j connection established")
                return self._driver
            
            except (ServiceUnavailable, DriverError) as e:
                last_error = e
                retries += 1
                wait_ms = self.config.retry_backoff_ms * retries
                logger.warning(
                    f"Connection attempt {retries}/{self.config.max_retries} "
                    f"failed. Retrying in {wait_ms}ms..."
                )
                await asyncio.sleep(wait_ms / 1000)
        
        raise RuntimeError(
            f"Failed to connect to Neo4j after {self.config.max_retries} attempts"
        ) from last_error
    
    async def session(self) -> AsyncSession:
        """Get an async session."""
        driver = await self.connect()
        return driver.session(database=self.config.database)
    
    async def close(self) -> None:
        """Close driver and clean up."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### 4.3 Repository Implementation

```python
# src/database/infrastructure/repository.py
from typing import Any
import logging
from neo4j import AsyncSession
from src.database.domain.repositories import (
    NodeRepository,
    RelationshipRepository,
    DatabaseRepository,
    QueryResult,
)
from src.database.domain.models import Node, Relationship

logger = logging.getLogger(__name__)

class Neo4jRepository:
    """Concrete Neo4j repository implementation."""
    
    def __init__(self, driver: Neo4jDriver):
        self.driver = driver
        self.nodes = self._NodeRepository(driver)
        self.relationships = self._RelationshipRepository(driver)
    
    class _NodeRepository(NodeRepository):
        """Node operations."""
        
        def __init__(self, driver: Neo4jDriver):
            self.driver = driver
        
        async def create_node(
            self,
            label: str,
            properties: dict[str, Any]
        ) -> dict[str, Any]:
            """Create node with auto-generated ID."""
            query = f"""
            CREATE (n:{label})
            SET n += $props
            RETURN elementId(n) as id, properties(n) as props
            """
            session = await self.driver.session()
            try:
                result = await session.run(query, props=properties)
                record = await result.single()
                return {
                    "id": record["id"],
                    "label": label,
                    **record["props"]
                }
            finally:
                await session.close()
        
        async def read_node(
            self,
            label: str,
            node_id: str
        ) -> dict[str, Any] | None:
            """Read node by ID."""
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
                        **record["props"]
                    }
                return None
            finally:
                await session.close()
        
        async def update_node(
            self,
            label: str,
            node_id: str,
            properties: dict[str, Any]
        ) -> dict[str, Any]:
            """Update node properties."""
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
                return {
                    "id": record["id"],
                    "label": label,
                    **record["props"]
                }
            finally:
                await session.close()
        
        async def delete_node(
            self,
            label: str,
            node_id: str
        ) -> bool:
            """Delete node."""
            query = f"""
            MATCH (n:{label})
            WHERE elementId(n) = $id
            DELETE n
            RETURN true
            """
            session = await self.driver.session()
            try:
                result = await session.run(query, id=node_id)
                return await result.single() is not None
            finally:
                await session.close()
        
        async def query(
            self,
            cypher: str,
            params: dict[str, Any] | None = None
        ) -> QueryResult:
            """Execute custom Cypher query."""
            import time
            session = await self.driver.session()
            try:
                start = time.time()
                result = await session.run(cypher, params or {})
                records = await result.fetch(None)  # Fetch all
                elapsed_ms = (time.time() - start) * 1000
                
                return QueryResult(
                    data=[dict(r) for r in records],
                    count=len(records),
                    execution_time_ms=elapsed_ms
                )
            finally:
                await session.close()
    
    class _RelationshipRepository(RelationshipRepository):
        """Relationship operations."""
        
        def __init__(self, driver: Neo4jDriver):
            self.driver = driver
        
        async def create_relationship(
            self,
            from_id: str,
            rel_type: str,
            to_id: str,
            properties: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            """Create relationship between nodes."""
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
                    props=properties or {}
                )
                record = await result.single()
                return {
                    "id": record["id"],
                    "from_id": from_id,
                    "to_id": to_id,
                    "rel_type": record["rel_type"],
                    **record["props"]
                }
            finally:
                await session.close()
        
        async def delete_relationship(
            self,
            from_id: str,
            rel_type: str,
            to_id: str
        ) -> bool:
            """Delete relationship."""
            query = f"""
            MATCH (from)-[r:{rel_type}]->(to)
            WHERE elementId(from) = $from_id AND elementId(to) = $to_id
            DELETE r
            RETURN true
            """
            session = await self.driver.session()
            try:
                result = await session.run(query, from_id=from_id, to_id=to_id)
                return await result.single() is not None
            finally:
                await session.close()
    
    async def transaction(
        self,
        operations: list[tuple[str, dict]]
    ) -> list[QueryResult]:
        """Execute operations in a transaction."""
        session = await self.driver.session()
        try:
            async with session.begin_transaction() as tx:
                results = []
                for cypher, params in operations:
                    result = await tx.run(cypher, params)
                    records = await result.fetch(None)
                    results.append(QueryResult(
                        data=[dict(r) for r in records],
                        count=len(records),
                        execution_time_ms=0
                    ))
            return results
        finally:
            await session.close()
    
    async def close(self) -> None:
        """Close repository."""
        await self.driver.close()
```

### 4.4 Schema Management

```python
# src/database/infrastructure/schema.py
from typing import Any
import logging

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manage schema: indexes, constraints, node labels."""
    
    def __init__(self, driver: Neo4jDriver):
        self.driver = driver
    
    async def setup_schema(self) -> None:
        """Initialize schema with indexes and constraints."""
        session = await self.driver.session()
        try:
            # Example: Create constraints
            constraints = [
                "CREATE CONSTRAINT unique_node_id IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT unique_user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
            ]
            
            for constraint in constraints:
                await session.run(constraint)
                logger.info(f"Applied constraint: {constraint}")
            
            # Example: Create indexes
            indexes = [
                "CREATE INDEX node_created_at IF NOT EXISTS FOR (n:Node) ON (n.created_at)",
                "CREATE INDEX user_status IF NOT EXISTS FOR (u:User) ON (u.status)",
            ]
            
            for index in indexes:
                await session.run(index)
                logger.info(f"Applied index: {index}")
        
        finally:
            await session.close()
        
        logger.info("Schema setup complete")
    
    async def drop_all(self, confirm: bool = False) -> None:
        """Drop all nodes and relationships (use with caution)."""
        if not confirm:
            raise ValueError("Must confirm with confirm=True")
        
        session = await self.driver.session()
        try:
            await session.run("MATCH (n) DETACH DELETE n")
            logger.warning("All nodes and relationships deleted")
        finally:
            await session.close()
    
    async def recreate_schema(self) -> None:
        """Drop and recreate schema (destructive)."""
        await self.drop_all(confirm=True)
        await self.setup_schema()
        logger.info("Schema recreated")
```

### 4.5 Reporting & Diagnostics

```python
# src/database/infrastructure/reporting.py
import logging
from typing import Any

logger = logging.getLogger(__name__)

class ReportingService:
    """Generate database overview and diagnostics."""
    
    def __init__(self, driver: Neo4jDriver, repository: Neo4jRepository):
        self.driver = driver
        self.repository = repository
    
    async def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics."""
        session = await self.driver.session()
        try:
            # Node count by label
            node_stats = await session.run("""
                CALL apoc.meta.stats() YIELD nodeCount, relCount
                RETURN nodeCount, relCount
            """)
            node_record = await node_stats.single()
            
            # Relationship count by type
            rel_stats = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            rel_records = await rel_stats.fetch(None)
            
            return {
                "total_nodes": node_record["nodeCount"] if node_record else 0,
                "total_relationships": node_record["relCount"] if node_record else 0,
                "relationships_by_type": {
                    r["rel_type"]: r["count"] for r in rel_records
                }
            }
        finally:
            await session.close()
    
    async def get_node_overview(self) -> dict[str, Any]:
        """Get node overview by label."""
        result = await self.repository.nodes.query("""
            CALL apoc.meta.stats() YIELD labels
            RETURN labels
        """)
        return result.data
    
    async def get_relationship_overview(self) -> dict[str, Any]:
        """Get relationship overview by type."""
        result = await self.repository.nodes.query("""
            CALL db.relationshipTypes() YIELD relationshipType
            RETURN relationshipType
        """)
        return result.data
    
    async def generate_full_report(self) -> dict[str, Any]:
        """Generate comprehensive database report."""
        stats = await self.get_database_stats()
        nodes = await self.get_node_overview()
        rels = await self.get_relationship_overview()
        
        return {
            "timestamp": str(__import__('datetime').datetime.now()),
            "statistics": stats,
            "node_overview": nodes,
            "relationship_overview": rels,
        }
```

---

## 5. Application Layer - Public API

```python
# src/database/manager.py
from typing import Any, Optional
from src.database.infrastructure.driver import Neo4jDriver
from src.database.infrastructure.repository import Neo4jRepository
from src.database.infrastructure.schema import SchemaManager
from src.database.infrastructure.reporting import ReportingService
from src.database.config import Neo4jSettings

class DatabaseManager:
    """High-level public API for database operations."""
    
    def __init__(self, settings: Optional[Neo4jSettings] = None):
        self.settings = settings or Neo4jSettings()
        self.driver = Neo4jDriver.get_instance(self.settings)
        self.repository: Optional[Neo4jRepository] = None
        self.schema: Optional[SchemaManager] = None
        self.reporting: Optional[ReportingService] = None
    
    async def initialize(self) -> None:
        """Initialize all components."""
        await self.driver.connect()
        self.repository = Neo4jRepository(self.driver)
        self.schema = SchemaManager(self.driver)
        self.reporting = ReportingService(self.driver, self.repository)
    
    async def setup_database(self) -> None:
        """Setup schema and prepare database."""
        await self.initialize()
        await self.schema.setup_schema()
    
    async def reset_database(self) -> None:
        """Reset database to clean state (destructive)."""
        await self.schema.recreate_schema()
    
    # Convenience methods for agents
    async def create_node(self, label: str, properties: dict) -> dict:
        """Create a node."""
        return await self.repository.nodes.create_node(label, properties)
    
    async def get_node(self, label: str, node_id: str) -> Optional[dict]:
        """Get node by ID."""
        return await self.repository.nodes.read_node(label, node_id)
    
    async def query(self, cypher: str, params: dict = None) -> Any:
        """Execute custom Cypher query."""
        return await self.repository.nodes.query(cypher, params)
    
    async def get_report(self) -> dict:
        """Get database overview report."""
        return await self.reporting.generate_full_report()
    
    async def close(self) -> None:
        """Close all connections."""
        await self.driver.close()
```

---

## 6. Orchestrator Integration

```python
# src/logic/orchestrate.py (updated)
from langgraph.graph import StateGraph
from typing import TypedDict, Any
from src.database.manager import DatabaseManager

class AgentState(TypedDict):
    """LangGraph state for agents."""
    messages: list[dict[str, str]]
    database: DatabaseManager
    context: dict[str, Any]

class HiveGuide:
    """Main orchestrator using LangGraph."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.graph = self._build_graph()
    
    async def initialize(self) -> None:
        """Initialize database on startup."""
        await self.db_manager.initialize()
        await self.db_manager.schema.setup_schema()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph with dependency injection."""
        workflow = StateGraph(AgentState)
        
        # Define nodes (agents)
        def agent_node(state: AgentState) -> AgentState:
            # Agents receive injected database manager
            db = state["database"]
            
            # Example: agents can now use:
            # - db.create_node()
            # - db.query()
            # - db.repository (for advanced operations)
            
            return state
        
        workflow.add_node("agent", agent_node)
        workflow.set_entry_point("agent")
        
        return workflow.compile()
    
    async def run(self, input_data: dict) -> dict:
        """Run orchestrator with injected database."""
        state = AgentState(
            messages=[],
            database=self.db_manager,
            context=input_data
        )
        return await self.graph.ainvoke(state)
    
    async def cleanup(self) -> None:
        """Cleanup on shutdown."""
        await self.db_manager.close()
```

---

## 7. Agent Usage Examples

```python
# Example: How agents use the database

async def knowledge_agent(state: AgentState) -> AgentState:
    """Example agent that creates and queries nodes."""
    db = state["database"]
    
    # Create a node
    knowledge_node = await db.create_node(
        label="Knowledge",
        properties={
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "created_at": datetime.now()
        }
    )
    
    # Query nodes
    result = await db.query("""
        MATCH (k:Knowledge)
        WHERE k.author = $author
        RETURN k
    """, params={"author": "Robert C. Martin"})
    
    state["context"]["knowledge"] = result.data
    return state

async def analysis_agent(state: AgentState) -> AgentState:
    """Example agent doing complex analysis."""
    db = state["database"]
    
    # Use repository for advanced operations
    result = await db.repository.nodes.query("""
        MATCH (k:Knowledge)-[r:REFERENCES]->(other:Knowledge)
        RETURN k.title, other.title, type(r)
    """)
    
    state["context"]["analysis"] = result.data
    return state
```

---

## 8. Setup & Initialization Flow

```python
# main.py example
import asyncio
from src.logic.orchestrate import HiveGuide

async def main():
    guide = HiveGuide()
    
    try:
        # Initialize database on startup
        await guide.initialize()
        
        # Get report before running agents
        report = await guide.db_manager.get_report()
        print(f"Database ready: {report}")
        
        # Run orchestrator with agents
        result = await guide.run({
            "user_query": "Analyze knowledge base"
        })
        
        # Get report after agents ran
        final_report = await guide.db_manager.get_report()
        print(f"Final state: {final_report}")
    
    finally:
        await guide.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Testing Strategy

```python
# tests/test_repository.py (example)
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.database.infrastructure.repository import Neo4jRepository

@pytest.mark.asyncio
async def test_create_node():
    """Test node creation."""
    # Mock driver
    mock_driver = AsyncMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value = mock_session
    
    # Setup mock response
    mock_result = MagicMock()
    mock_result.single = AsyncMock(return_value={
        "id": "node-123",
        "props": {"title": "Test"}
    })
    mock_session.run.return_value = mock_result
    
    # Test
    repo = Neo4jRepository(mock_driver)
    node = await repo.nodes.create_node("Test", {"title": "Test"})
    
    assert node["id"] == "node-123"
    assert node["title"] == "Test"
```

---

## 10. Key Benefits of This Approach

✅ **Clean Separation:** Domain layer isolated from infrastructure  
✅ **Testability:** Mock repositories for unit tests without Neo4j  
✅ **Type Safety:** Full type hints with Protocol interfaces  
✅ **Scalability:** Async operations for I/O efficiency  
✅ **Maintainability:** Single responsibility per class  
✅ **Flexibility:** Agents inject database, orchestrator controls lifecycle  
✅ **Error Handling:** Explicit exceptions, retry logic, logging  
✅ **Configuration:** Environment-driven via Pydantic Settings  

---

## 11. Implementation Sequence

1. **Phase 1:** Domain models + Protocols
2. **Phase 2:** Config + Driver management
3. **Phase 3:** Repository implementation
4. **Phase 4:** Schema management + Reporting
5. **Phase 5:** Public manager API
6. **Phase 6:** Orchestrator integration
7. **Phase 7:** Tests + Documentation

---

**Ready to implement?** Approve this approach or request modifications.
