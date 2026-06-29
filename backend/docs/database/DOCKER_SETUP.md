# Docker Setup Guide for HIVE

This guide explains how to use Docker Compose to run Neo4j with persistent storage for the HIVE knowledge base system.

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker and Docker Compose)
- Python 3.14+ with the HIVE dependencies installed

### Start Neo4j Database

```bash
# From the project root directory
docker-compose up -d
```

This starts:
- **Neo4j Database**: Running on `bolt://neo4j:7687` (internal) or `bolt://localhost:7687` (external)
- **Persistent Volumes**: Data stored in Docker volumes

### Verify Connection

```bash
# Check that Neo4j is running
docker-compose ps

# View Neo4j logs
docker-compose logs neo4j

# Access Neo4j Browser (web UI)
# Open http://localhost:7474 in your browser
# Default credentials: neo4j / password
```

## Architecture

### Services

**neo4j**: Neo4j 5.x database server
- HTTP UI: `http://localhost:7474`
- HTTP API: `http://localhost:7473`
- Bolt Protocol: `bolt://localhost:7687` (default driver connection)

### Volumes (Persistent Storage)

- `neo4j_data`: Database data files (persists across restarts)
- `neo4j_logs`: Database logs
- `neo4j_import`: Import directory for bulk loading

All volumes are stored in Docker's data directory and **persist when containers are stopped**.

## Connection Configuration

### From Host Machine
```python
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)
```

### From Docker Container (via service name)
```python
driver = AsyncGraphDatabase.driver(
    "bolt://neo4j:7687",  # Uses Docker DNS
    auth=("neo4j", "password")
)
```

### Auto-Detection
The HIVE system automatically detects Docker environment and connects to the appropriate host:
- **In Docker**: Uses `bolt://neo4j:7687`
- **Locally**: Uses `bolt://localhost:7687`

## Environment Variables

Create a `.env` or `.env.docker` file:

```bash
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
NEO4J_MAX_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT_S=30.0
```

The system reads environment variables with `NEO4J_` prefix via Pydantic Settings.

## Running the Application

### Option 1: Local Development (Database in Docker)

```bash
# Terminal 1: Start Neo4j
docker-compose up neo4j

# Terminal 2: Run Python application locally
export NEO4J_URI=bolt://localhost:7687
python main.py --mode write --text "Sample text"
```

### Option 2: Full Docker (Application + Database)

```bash
# Build and run everything
docker-compose up

# Or build only if image doesn't exist
docker-compose up --build
```

### Option 3: Use in Jupyter Notebook

See `knowledge_base_test.ipynb` for the interactive testing harness with built-in Docker detection and visualization.

The notebook includes:
1. Automatic Docker Neo4j startup if available
2. Interactive graph visualization with `pyvis`
3. Database statistics and query tools
4. Knowledge base exploration

## Data Persistence

### Stop Container (Keeps Data)
```bash
docker-compose stop
# or
docker-compose down
```

Data persists in volumes and can be recovered by restarting:
```bash
docker-compose up -d
```

### Delete All Data
```bash
docker-compose down -v
# -v flag removes volumes
```

### Backup Database
```bash
# Export database dump
docker exec hive-neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/dumps

# Copy to host
docker cp hive-neo4j:/var/lib/neo4j/dumps ./neo4j_backup
```

## Management Commands

### View Database
```bash
# Open Neo4j Browser
# http://localhost:7474

# Query with cypher-shell
docker exec -it hive-neo4j cypher-shell -u neo4j -p password
```

### Health Check
```bash
docker-compose ps
# neo4j should show "healthy"
```

### Restart Service
```bash
docker-compose restart neo4j
```

### View Logs
```bash
docker-compose logs -f neo4j
# Press Ctrl+C to exit
```

## Configuration Reference

### docker-compose.yml Environment Variables

```yaml
NEO4J_AUTH: neo4j/password          # Default credentials
NEO4J_server_memory_heap_initial__size: 512m   # Initial heap
NEO4J_server_memory_heap_max__size: 1g         # Max heap
NEO4J_server_memory_pagecache_size: 256m       # Page cache
NEO4J_dbms_security_procedures_unrestricted: "apoc..*"  # APOC procedures
```

Adjust these based on your system resources.

## Troubleshooting

### Connection Refused
```bash
# Check if container is running
docker-compose ps

# Check logs
docker-compose logs neo4j

# Restart
docker-compose restart neo4j
```

### Port Already in Use
```bash
# Change ports in docker-compose.yml
# OR kill existing process
lsof -i :7687  # Find what's using port 7687
```

### Docker Not Found
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
```

### Out of Memory
```bash
# Increase Docker Desktop memory allocation:
# Docker Desktop > Settings > Resources > Memory
# Recommended: 4GB+ for comfortable development
```

## Next Steps

1. **Start the database**: `docker-compose up -d`
2. **Run the notebook**: Open `knowledge_base_test.ipynb`
3. **Load sample data**: Execute the write workflow cells
4. **Visualize**: Run the visualization cells to see the knowledge graph
5. **Explore**: Use the query cells to inspect your data

## References

- [Neo4j Docker Image](https://hub.docker.com/_/neo4j)
- [Neo4j Operations Manual](https://neo4j.com/docs/operations-manual/current/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
