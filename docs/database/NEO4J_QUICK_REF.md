# Neo4j Quick Reference

## Import & Initialize

```python
from src.database import DatabaseManager

db = DatabaseManager()
await db.initialize()
```

## Node Operations

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

## Relationships

```python
# Create
rel = await db.create_relationship(from_id, "REL_TYPE", to_id, {"prop": "val"})

# Delete
success = await db.delete_relationship(from_id, "REL_TYPE", to_id)
```

## Queries

```python
# Simple query
result = await db.query("MATCH (n) RETURN n LIMIT 10")

# Parameterized query
result = await db.query(
    "MATCH (u:User) WHERE u.name = $name RETURN u",
    {"name": "Alice"}
)

# Access results
for row in result["data"]:
    print(row)
print(f"Execution time: {result['execution_time_ms']}ms")
```

## Transactions

```python
results = await db.transaction([
    ("CREATE (u:User {name: $name}) RETURN u", {"name": "Alice"}),
    ("CREATE (u:User {name: $name}) RETURN u", {"name": "Bob"}),
])
```

## Database Management

```python
# Setup schema (constraints, indexes)
await db.setup_database()

# Get statistics
stats = await db.get_stats()

# Full report (stats + node/relationship overview)
report = await db.get_report()

# Reset database (destructive!)
await db.reset_database()
```

## Configuration

**Target profile** (`NEO4J_TARGET`):
- `local` (default) — `bolt://localhost:7687` on host, `bolt://neo4j:7687` in Docker
- `hosted` — remote Aura / cloud instance via `NEO4J_HOSTED_*` (see below)
- `docker` — same as local (Compose service hostname when inside Docker)

Environment variables (NEO4J_ prefix):
- `NEO4J_URI` - Connection URI (overrides local default when set)
- `NEO4J_USERNAME` - Database user (default: neo4j)
- `NEO4J_PASSWORD` - Database password (default: password)
- `NEO4J_DATABASE` - Database name (default: neo4j)
- `NEO4J_MAX_POOL_SIZE` - Connection pool size (default: 50)
- `NEO4J_DEBUG` - Enable debug logging (default: false)

**Hosted / Aura** (when `NEO4J_TARGET=hosted`):
- `NEO4J_HOSTED_NAME` - Instance id → `neo4j+s://{id}.databases.neo4j.io`
- `NEO4J_HOSTED_PASSWORD` - Database password (required)
- `NEO4J_HOSTED_URI` - Full URI (optional, overrides `HOSTED_NAME`)
- `NEO4J_HOSTED_USERNAME`, `NEO4J_HOSTED_DATABASE` - Optional overrides

Or use `.env` file or pass `Neo4jSettings` / `Neo4jSettings.for_target("hosted")` to constructor.

## In Agents (with Orchestrator)

```python
async def my_agent(state: AgentState) -> AgentState:
    db = state["database"]  # Injected DatabaseManager
    
    # Use database...
    node = await db.create_node("Entity", {"data": "value"})
    result = await db.query("MATCH (n:Entity) RETURN n")
    
    state["output"] = result
    return state
```

## Error Handling

```python
try:
    await db.initialize()
except RuntimeError:
    # Connection failed
    pass
except Exception as e:
    # Other errors
    pass
finally:
    await db.close()
```

## Best Practices

✓ **Always close**: Call `await db.close()` when done  
✓ **Use context manager**: `async with DatabaseManager() as db:`  
✓ **Parameterize queries**: Prevents injection attacks  
✓ **Use transactions**: For multiple related operations  
✓ **Handle errors**: Catch and log exceptions  
✓ **Confirmation for destructive ops**: `confirm=True` for reset

---

## Documents

- [NEO4J_USAGE.md](NEO4J_USAGE.md) - Comprehensive usage guide
- [NEO4J_APPROACH.md](NEO4J_APPROACH.md) - Architecture details
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was implemented
