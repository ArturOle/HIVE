# Hosted Neo4j (Aura) Setup Guide

This guide walks you through using **Neo4j Aura** (managed cloud service) with ReLived.

## Why Hosted Neo4j?

✅ **No infrastructure management** - Neo4j handles backups, updates, scaling  
✅ **Production-ready** - High availability, encryption, monitoring built-in  
✅ **Secure** - Encrypted connections (neo4j+s://)  
✅ **Scalable** - Easily upgrade instance size  
✅ **Free tier available** - Start with 500k nodes/relationships free  

---

## Step 1: Create Neo4j Aura Instance

1. Go to https://neo4j.com/cloud/aura/
2. Click "Start Free"
3. Sign up or log in
4. Create a new instance:
   - **Name**: `relived-prod` (or any name)
   - **Type**: Free (recommended to start)
   - **Region**: Choose closest to you
5. Click "Create"
6. **IMPORTANT**: Copy the connection details:
   - **Connection String**: `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - **Username**: `neo4j`
   - **Password**: (shown once - save it!)
   - **Instance ID**: Extract from connection string (the `xxxxxxxx` part)

---

## Step 2: Configure ReLived

### Create `.env` file in project root:

```env
# Use hosted Neo4j
NEO4J_TARGET=hosted

# From your Aura console:
NEO4J_HOSTED_NAME=xxxxxxxx          # Instance ID (without domain)
NEO4J_HOSTED_PASSWORD=your_password # Your instance password

# Optional: override connection string (auto-built from HOSTED_NAME)
# NEO4J_HOSTED_URI=neo4j+s://xxxxxxxx.databases.neo4j.io

# Username (default is "neo4j", but you can override)
# NEO4J_HOSTED_USERNAME=neo4j

# Database name (default is "neo4j")
# NEO4J_HOSTED_DATABASE=neo4j

# LLM Provider (optional, for better extraction)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
```

### Verify your `.env`:

```bash
# Check file exists
ls -la .env

# Verify it has the right values
cat .env | grep NEO4J_
```

---

## Step 3: Start ReLived with Docker

### Option A: Docker Compose (Simplest)

```bash
# Start backend + frontend (connects to your Aura instance)
docker-compose up -d

# Check logs
docker-compose logs -f backend_api

# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

### Option B: Local Python (For Development)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt
python -m uvicorn api:app --reload

# In another terminal
cd frontend
pip install -r requirements.txt
streamlit run src/main.py
```

---

## Step 4: Verify Connection

### Test Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### Test Neo4j Connection

```bash
curl -X POST http://localhost:8000/read \
  -H "Content-Type: application/json" \
  -d '{"query": "test connection", "top_k": 3}'
```

### View API Documentation

Open http://localhost:8000/docs in browser (Swagger UI)

---

## Step 5: Ingest Knowledge

### Using the Jupyter Notebook

1. Navigate to `backend/knowledge_base_test.ipynb`
2. Set configuration:
   ```python
   PROVIDER = "openai"           # or "gemini", "inception"
   EMBEDDER_PROVIDER = "openai"  # or "gemini", "qwen"
   NEO4J_TARGET = "hosted"       # Use hosted
   ```
3. Run cells to ingest knowledge from `backend/data/` files

### Using the Backend API

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your knowledge text here",
    "environment_hint": "general"
  }'
```

---

## Step 6: Query Your Knowledge

### Using Frontend

1. Open http://localhost:8501
2. Type questions in the chat box
3. Adjust "Top-K Results" in sidebar
4. View responses from your Neo4j knowledge base

### Using API

```bash
curl -X POST http://localhost:8000/read \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I handle motor overheating?", "top_k": 5}'
```

---

## Managing Your Aura Instance

### Scale Your Instance

1. Go to your Aura console
2. Click your instance
3. Click "Settings"
4. Under "Instance Details", click "Upgrade"
5. Choose new size and confirm

### Monitor Performance

1. Go to your Aura instance dashboard
2. View metrics:
   - Disk usage
   - CPU usage
   - Connection count
   - Query statistics

### Backup & Restore

- **Automatic backups**: Neo4j Aura automatically backs up daily
- **Manual export**: Use Neo4j Bloom or cypher-shell
- **Snapshot**: In Aura console, create a backup snapshot

---

## Security Best Practices

### 1. Keep Credentials Safe

❌ **Never** commit `.env` to git  
✅ **Do** add `.env` to `.gitignore`

```bash
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

### 2. Use Environment Variables in Production

```bash
# Instead of .env, set via environment
export NEO4J_TARGET=hosted
export NEO4J_HOSTED_PASSWORD=your_password
export NEO4J_HOSTED_NAME=instance_id

# Start app
docker-compose up
```

### 3. Rotate Your Password

1. Go to Aura console
2. Click your instance
3. Go to "Details" → "Manage Password"
4. Update `.env` with new password
5. Restart ReLived

### 4. Use Network Controls (Pro Plan)

If using Aura Pro, configure IP whitelisting:
1. Go to instance settings
2. Add your IP addresses
3. Only those IPs can connect

---

## Troubleshooting

### "Hosted Neo4j credentials not configured"

**Problem**: Backend fails to start with this error

**Solution**:
```bash
# 1. Check .env exists
ls -la .env

# 2. Verify it has the right keys
grep NEO4J_TARGET .env
grep NEO4J_HOSTED_PASSWORD .env
grep NEO4J_HOSTED_NAME .env

# 3. Check for typos in variable names (case-sensitive)
# 4. Restart backend after editing .env
```

### Connection Timeout

**Problem**: `[Errno 110] Connection timed out`

**Solution**:
1. Verify instance is running (check Aura console)
2. Check internet connectivity
3. Try manual cypher-shell test:
   ```bash
   cypher-shell -a neo4j+s://instance.databases.neo4j.io \
     -u neo4j -p your_password \
     "RETURN 1"
   ```

### "Neo4j Password Required" in Notebook

**Problem**: Jupyter notebook asks for password

**Solution**:
```python
# In notebook setup cell:
load_project_env(override=False)  # Loads .env

# Or set environment variable manually:
import os
os.environ["NEO4J_HOSTED_PASSWORD"] = "your_password"
```

### High Query Latency

**Problem**: Queries taking 10+ seconds

**Solution**:
1. Check Neo4j Aura metrics (CPU, disk, queries)
2. Reduce `top_k` value (fewer results = faster)
3. Add database indexes:
   ```python
   # In notebook or backend
   await orchestrator.db.setup_database()  # Creates indexes
   ```
4. Consider upgrading instance size

---

## Monitoring & Logging

### Docker Container Logs

```bash
# View backend logs
docker-compose logs backend_api -f

# View frontend logs
docker-compose logs frontend -f

# View all logs
docker-compose logs -f
```

### Backend Debug Logging

```bash
# Increase log verbosity
cd backend
python -m uvicorn api:app --log-level debug
```

### Neo4j Query Logging

Enable in Aura console:
1. Go to instance settings
2. Find "Logging" section
3. Enable query logging
4. Query log appears in console

---

## Performance Tips

### 1. Use Embeddings

Set up OpenAI or Gemini embeddings for better semantic search:
```env
EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 2. Batch Writes

Insert multiple knowledge entries at once:
```bash
# Much faster than one-by-one
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '[
    {"text": "knowledge 1"},
    {"text": "knowledge 2"},
    {"text": "knowledge 3"}
  ]'
```

### 3. Create Indexes

Database setup automatically creates indexes:
```python
await orchestrator.db.setup_database()
```

### 4. Monitor Query Performance

Check slow queries in Aura dashboard:
- Queries taking 1+ second
- High memory usage
- Connection count

---

## Next Steps

1. ✅ **Set up instance** (you are here)
2. ⬜ **Ingest knowledge** → Use notebook or API to load data
3. ⬜ **Configure LLM** → Set up OpenAI/Gemini for extraction
4. ⬜ **Query in chat** → Ask questions in Streamlit frontend
5. ⬜ **Deploy to production** → Use Docker in cloud (GCP, AWS, etc.)

---

## Support

- **Aura Issues**: https://support.neo4j.com
- **ReLived Issues**: Check [QUICKSTART.md](../QUICKSTART.md)
- **Neo4j Docs**: https://neo4j.com/docs/aura/

---

## Cost Estimation

### Neo4j Aura Pricing

| Plan | Nodes | Price | Best For |
|------|-------|-------|----------|
| **Free** | 500k | Free | Development, learning |
| **Professional** | Unlimited | From $99/mo | Production |
| **Enterprise** | Unlimited | Custom | Large scale |

For ReLived's typical use case:
- **Small knowledge base** (< 100k nodes) → Free tier
- **Medium** (100k-1M nodes) → Professional $99/mo
- **Large** (> 1M nodes) → Enterprise plan

---

**Happy querying! 🧠**
