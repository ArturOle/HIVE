# Neo4j Integration - Implementation & Usage Guide

This document provides comprehensive guidance on using the ReLive Neo4j database management system.

## Quick Start

### 1. Basic Database Operations

```python
import asyncio
from src.database import DatabaseManager

async def main():
    # Create and initialize database manager
    db = DatabaseManager()
    await db.initialize()
    
    # Setup schema (constraints, indexes)
    await db.setup_database()
    
    # Create a node
    user = await db.create_node("User", {
        "name": "Alice",
        "email": "alice@example.com",
        "status": "active"
    })
    print(f"Created user: {user['id']}")
    
    # Get a node
    retrieved = await db.get_node("User", user["id"])
    print(f"Retrieved: {retrieved}")
    
    # Update node
    updated = await db.update_node("User", user["id"], {
        "status": "inactive"
    })
    print(f"Updated: {updated}")
    
    # Delete node
    deleted = await db.delete_node("User", user["id"])
    print(f"Deleted: {deleted}")
    
    # Cleanup
    await db.close()

asyncio.run(main())
```

### 2. Relationships

```python
async def relationships_example():
    db = DatabaseManager()
    await db.initialize()
    
    # Create two nodes
    alice = await db.create_node("User", {"name": "Alice"})
    bob = await db.create_node("User", {"name": "Bob"})
    
    # Create relationship
    rel = await db.create_relationship(
        from_id=alice["id"],
        rel_type="KNOWS",
        to_id=bob["id"],
        properties={"since": 2023}
    )
    print(f"Created relationship: {rel}")
    
    # Delete relationship
    deleted = await db.delete_relationship(
        from_id=alice["id"],
        rel_type="KNOWS",
        to_id=bob["id"]
    )
    print(f"Deleted: {deleted}")
    
    await db.close()
```

### 3. Custom Cypher Queries

```python
async def query_example():
    db = DatabaseManager()
    await db.initialize()
    
    # Simple query
    result = await db.query("""
        MATCH (u:User)
        WHERE u.status = $status
        RETURN u.name, u.email
        LIMIT 10
    """, params={"status": "active"})
    
    print(f"Found {result['count']} users")
    for row in result["data"]:
        print(row)
    
    # Complex query with relationships
    result = await db.query("""
        MATCH (a:User)-[k:KNOWS]->(b:User)
        WHERE a.name = $name
        RETURN a.name, b.name, k.since
    """, params={"name": "Alice"})
    
    await db.close()
```

### 4. Transactions

```python
async def transaction_example():
    db = DatabaseManager()
    await db.initialize()
    
    # Execute multiple operations atomically
    results = await db.transaction([
        (
            "CREATE (u:User {name: $name}) RETURN u",
            {"name": "Charlie"}
        ),
        (
            "CREATE (u:User {name: $name}) RETURN u",
            {"name": "Diana"}
        ),
    ])
    
    print(f"Transaction created {len(results)} users")
    await db.close()
```

### 5. Database Reports

```python
async def reporting_example():
    db = DatabaseManager()
    await db.initialize()
    
    # Get comprehensive report
    report = await db.get_report()
    print(f"Total nodes: {report['statistics']['total_nodes']}")
    print(f"Total relationships: {report['statistics']['total_relationships']}")
    print(f"Nodes by label: {report['statistics']['node_count_by_label']}")
    
    # Get stats only
    stats = await db.get_stats()
    print(f"Stats: {stats}")
    
    await db.close()
```

---

## Using with LangGraph Orchestrator

The `HiveGuide` orchestrator automatically injects the database manager into agent state.

### Example: Creating an Agent

```python
from src.logic.orchestrator import HiveGuide, AgentState

async def main():
    guide = HiveGuide()
    await guide.initialize()
    
    # Run orchestrator - database is injected
    result = await guide.run({
        "user_query": "Create knowledge nodes"
    })
    
    print(f"Result: {result['output']}")
    await guide.cleanup()
```

### Example: Agent Accessing Database

Agents receive `AgentState` with injected database:

```python
from src.logic.orchestrator import AgentState
from src.database import DatabaseManager

# This would be a node in the LangGraph
async def knowledge_extraction_agent(state: AgentState) -> AgentState:
    """Agent that extracts and stores knowledge."""
    db: DatabaseManager = state["database"]
    user_query = state["context"]["user_query"]
    
    # Create knowledge nodes
    knowledge = await db.create_node("Knowledge", {
        "text": "Sample knowledge",
        "source": "user_input",
        "created_at": datetime.now().isoformat()
    })
    
    # Query existing knowledge
    result = await db.query("""
        MATCH (k:Knowledge)
        WHERE k.source = $source
        RETURN k
        ORDER BY k.created_at DESC
        LIMIT 10
    """, params={"source": "user_input"})
    
    state["output"] = {
        "created_node": knowledge,
        "similar_knowledge": result["data"]
    }
    
    return state
```

---

## Configuration

Neo4j connection settings are configured via environment variables or `.env` file:

### Environment Variables

```bash
# Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Connection pool
NEO4J_MAX_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT_S=30

# Retry logic
NEO4J_MAX_RETRIES=3
NEO4J_RETRY_BACKOFF_MS=100

# Debug
NEO4J_DEBUG=false
```

### .env File

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=secure_password
NEO4J_DATABASE=neo4j
```

### Programmatic Configuration

```python
from src.database import DatabaseManager, Neo4jSettings

settings = Neo4jSettings(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password",
    database="neo4j",
    debug=True
)

db = DatabaseManager(settings)
await db.initialize()
```

---

## Architecture Overview

### Layer Structure

```
┌─────────────────────────────────┐
│  Agents (src/ai/)               │
└────────────┬────────────────────┘
             │
┌────────────▼─────────────────────┐
│  Orchestrator (src/logic/)       │
│  - Dependency Injection          │
│  - State Management              │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│  DatabaseManager (Public API)    │
│  - High-level operations         │
│  - Lifecycle management          │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│  Infrastructure Layer            │
│  - Driver (connection pooling)   │
│  - Repository (CRUD + queries)   │
│  - Schema (setup, recreate)      │
│  - Reporting (diagnostics)       │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│  Domain Layer (Protocols)        │
│  - NodeRepository                │
│  - RelationshipRepository        │
│  - Models (Pydantic)             │
└────────────┬─────────────────────┘
             │
            Neo4j Database
```

### Design Patterns

**1. Singleton Pattern (Driver)**
- One connection pool per application
- Lazy initialization with thread-safe instance retrieval

**2. Repository Pattern**
- Abstracts database queries behind clean interfaces
- Protocol-based for testability

**3. Dependency Injection**
- Database manager injected into agent state
- Orchestrator manages lifecycle

**4. Composition Over Inheritance**
- Repository composes NodeRepository and RelationshipRepository
- Clean separation of concerns

---

## API Reference

### DatabaseManager

#### Initialization
```python
db = DatabaseManager()
await db.initialize()
```

#### Node Operations
```python
# Create
node = await db.create_node("Label", {"prop": "value"})

# Read
node = await db.get_node("Label", node_id)

# Update
node = await db.update_node("Label", node_id, {"prop": "new_value"})

# Delete
success = await db.delete_node("Label", node_id)
```

#### Relationship Operations
```python
# Create
rel = await db.create_relationship(from_id, "REL_TYPE", to_id, {"prop": "value"})

# Delete
success = await db.delete_relationship(from_id, "REL_TYPE", to_id)
```

#### Query Operations
```python
# Custom query
result = await db.query("MATCH (n) RETURN n", {"param": "value"})

# Transaction
results = await db.transaction([
    ("MATCH (n) RETURN n", {}),
    ("CREATE (n:Node) RETURN n", {})
])
```

#### Reporting
```python
# Full report
report = await db.get_report()

# Statistics only
stats = await db.get_stats()

# Reset/setup
await db.setup_database()       # Setup schema
await db.reset_database()       # Drop and recreate (destructive!)
```

#### Lifecycle
```python
await db.close()
```

---

## Error Handling

All database operations raise appropriate exceptions:

```python
import logging
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)

async def safe_database_operation():
    db = DatabaseManager()
    
    try:
        await db.initialize()
        node = await db.create_node("User", {"name": "Alice"})
    except RuntimeError as e:
        logger.error(f"Database initialization failed: {e}")
    except ServiceUnavailable as e:
        logger.error(f"Neo4j service unavailable: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await db.close()
```

---

## Testing

### Unit Tests (Mock Repository)

```python
import pytest
from unittest.mock import AsyncMock
from src.database import DatabaseManager

@pytest.mark.asyncio
async def test_create_node():
    # Mock the driver
    db = DatabaseManager()
    db.repository = AsyncMock()
    db.repository.nodes.create_node.return_value = {
        "id": "test-id",
        "label": "Test",
        "name": "Test Node"
    }
    
    # Test
    node = await db.create_node("Test", {"name": "Test Node"})
    assert node["id"] == "test-id"
    db.repository.nodes.create_node.assert_called_once()
```

### Integration Tests (Real Database)

```python
import pytest
from testcontainers.neo4j import Neo4jContainer

@pytest.fixture
async def neo4j_database():
    """Fixture providing real Neo4j container for testing."""
    container = Neo4jContainer()
    container.start()
    
    settings = Neo4jSettings(
        uri=container.get_bolt_connection_uri(),
        username="neo4j",
        password="password"
    )
    
    db = DatabaseManager(settings)
    await db.initialize()
    await db.setup_database()
    
    yield db
    
    container.stop()

@pytest.mark.asyncio
async def test_create_and_query_node(neo4j_database):
    db = neo4j_database
    
    # Create
    node = await db.create_node("User", {"name": "Alice"})
    
    # Query
    result = await db.query("MATCH (u:User) RETURN u.name")
    assert result["count"] == 1
    assert result["data"][0]["u.name"] == "Alice"
```

---

## Best Practices

### 1. Always Call close()

```python
db = DatabaseManager()
try:
    await db.initialize()
    # ... operations ...
finally:
    await db.close()

# Or use context manager
async with DatabaseManager() as db:
    # ... operations ...
```

### 2. Use Transactions for Multiple Operations

```python
# ✓ Good - atomic
results = await db.transaction([
    ("CREATE (u:User {name: $name})", {"name": "Alice"}),
    ("CREATE (u:User {name: $name})", {"name": "Bob"}),
])

# ✗ Avoid - not atomic
await db.create_node("User", {"name": "Alice"})
await db.create_node("User", {"name": "Bob"})
```

### 3. Parameterize Queries

```python
# ✓ Good - safe from injection
result = await db.query(
    "MATCH (u:User) WHERE u.name = $name RETURN u",
    {"name": user_input}
)

# ✗ Bad - injection vulnerability
result = await db.query(
    f"MATCH (u:User) WHERE u.name = '{user_input}' RETURN u"
)
```

### 4. Use Logging

```python
import logging

logger = logging.getLogger(__name__)

async def agent_with_logging():
    db = DatabaseManager()
    logger.info("Initializing database")
    await db.initialize()
    
    logger.debug(f"Creating node: {node_data}")
    node = await db.create_node("User", node_data)
    
    logger.info(f"Created node with id: {node['id']}")
```

### 5. Handle Destructive Operations Carefully

```python
# ✓ Good - explicit confirmation
if confirm_reset:
    logger.warning("Resetting database")
    await db.reset_database()

# ✗ Avoid - accidental data loss
await db.reset_database()  # Too easy to call by mistake!
```

---

## Troubleshooting

### Connection Refused

```
RuntimeError: Failed to connect to Neo4j after 3 attempts
```

**Solution:**
- Ensure Neo4j is running: `docker-compose up -d neo4j` (or your setup)
- Check connection settings: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- Verify port 7687 is accessible

### Node Not Found

```
RuntimeError: Node with label User and id abc123 not found
```

**Solution:**
- Verify the node exists first
- Check the label spelling
- Use query to find nodes: `MATCH (n:User) RETURN n LIMIT 5`

### Constraint Violation

```
Exception: Constraint validation failed
```

**Solution:**
- Check for duplicate unique properties
- Review schema constraints
- Use UNIQUE constraints intentionally

---

## Performance Tuning

### Connection Pool Size

```python
settings = Neo4jSettings(
    max_pool_size=50  # Increase for high concurrency
)
```

### Query Optimization

```python
# ✓ Efficient - uses index
result = await db.query("MATCH (u:User) WHERE u.id = $id RETURN u", {"id": user_id})

# ✗ Slow - full table scan
result = await db.query("MATCH (u:User) RETURN u")
```

### Batch Operations

```python
# Create multiple nodes efficiently
operations = [(f"CREATE (n:User {{name: $name}}) RETURN n", {"name": name}) 
              for name in names]
results = await db.transaction(operations)
```

---

## Example Agent Implementation

Complete example of an agent using the database:

```python
from src.logic.orchestrator import AgentState
from src.database import DatabaseManager
from datetime import datetime

async def content_analyzer_agent(state: AgentState) -> AgentState:
    """Agent that analyzes and stores content."""
    db: DatabaseManager = state["database"]
    content = state["context"].get("content", "")
    
    # Create content node
    content_node = await db.create_node("Content", {
        "text": content,
        "analyzed_at": datetime.now().isoformat(),
        "status": "pending_analysis"
    })
    
    # Find related content
    similar = await db.query("""
        MATCH (c:Content)
        WHERE c.text CONTAINS $keyword
        AND c.status = $status
        RETURN c
        LIMIT 5
    """, params={
        "keyword": content[:20],  # First 20 chars as keyword
        "status": "analyzed"
    })
    
    # Update status
    await db.update_node("Content", content_node["id"], {
        "status": "analyzed"
    })
    
    # Create relationships to similar content
    for sim in similar["data"]:
        await db.create_relationship(
            content_node["id"],
            "SIMILAR_TO",
            sim.get("c").id,
            {"score": 0.8}
        )
    
    state["output"] = {
        "created_node_id": content_node["id"],
        "similar_count": len(similar["data"])
    }
    
    return state
```

---

For more examples and questions, see `NEO4J_APPROACH.md` for architecture details.
