# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.11+
- Neo4j (Hosted Aura or Docker)
- LLM Provider (optional: OpenAI or Gemini)

### ⚡ Quick Setup with Hosted Neo4j

1. **Get Neo4j credentials from Neo4j Aura:**
   - Create a free account: https://neo4j.com/cloud/aura/
   - Create an instance and get the connection details
   
2. **Configure environment** (`.env` in project root):
   ```env
   # Neo4j Hosted (Aura)
   NEO4J_TARGET=hosted
   NEO4J_HOSTED_NAME=your-instance-id  # e.g., "97f8db06"
   NEO4J_HOSTED_PASSWORD=your-password  # From Aura console
   
   # Optional: Override URI and username
   # NEO4J_HOSTED_URI=neo4j+s://instance.databases.neo4j.io
   # NEO4J_HOSTED_USERNAME=neo4j
   # NEO4J_HOSTED_DATABASE=neo4j
   
   # Optional: LLM Provider
   # LLM_PROVIDER=openai
   # OPENAI_API_KEY=sk-...
   ```

3. **Run with Docker Compose** (easiest):
   ```bash
   docker-compose up
   ```
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000

4. **Or run locally**:
   ```bash
   # Terminal 1: Backend
   cd backend
   pip install -r requirements.txt
   python -m uvicorn api:app --reload
   
   # Terminal 2: Frontend
   cd frontend
   pip install -r requirements.txt
   export BACKEND_URL=http://localhost:8000
   streamlit run src/main.py
   ```

---

## Option 2: Local Development with Docker Neo4j

For development, use the included Docker Neo4j instance:

```bash
# Start with local Neo4j profile
docker-compose --profile local up

# Or manually
docker-compose --profile local up neo4j
```

Update `.env`:
```env
NEO4J_TARGET=local
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## 📝 Full Configuration

### Environment Variables (.env)

```env
# Neo4j Target
NEO4J_TARGET=hosted         # or "local", "docker"

# ===== Hosted Neo4j (Neo4j Aura) =====
NEO4J_HOSTED_NAME=instance-id              # REQUIRED for hosted
NEO4J_HOSTED_PASSWORD=your-password        # REQUIRED for hosted
NEO4J_HOSTED_URI=neo4j+s://...             # Optional (auto-built from NAME)
NEO4J_HOSTED_USERNAME=neo4j                # Optional (default: neo4j)
NEO4J_HOSTED_DATABASE=neo4j                # Optional (default: neo4j)

# ===== Local Neo4j =====
NEO4J_URI=bolt://localhost:7687            # For local/docker target
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# ===== LLM Provider =====
LLM_PROVIDER=none                          # "openai", "gemini", or "none"
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# ===== Backend =====
BACKEND_URL=http://localhost:8000          # Used by frontend
```

---

## 🧪 Verify Setup

### Health Check
```bash
curl http://localhost:8000/health
```

### Test Read Query
```bash
curl -X POST http://localhost:8000/read \
  -H "Content-Type: application/json" \
  -d '{"query": "How to fix motor overheat?", "top_k": 5}'
```

### API Docs
Open http://localhost:8000/docs in browser (Swagger UI)

---

## 🔧 Common Tasks

### Use Different Neo4j Instance
Edit `.env` and change `NEO4J_HOSTED_NAME` or `NEO4J_HOSTED_URI`.

### Switch to Local Neo4j
```bash
# Update .env
NEO4J_TARGET=local

# Start Docker Neo4j
docker-compose --profile local up neo4j

# Restart backend
```

### View API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Debug Backend
```bash
cd backend
python -m uvicorn api:app --reload --log-level debug
```

### Clear Chat History
Click "Clear Conversation" button in Streamlit sidebar.

---

## 🆘 Troubleshooting

### "Hosted Neo4j credentials not configured"
- ✅ Set `NEO4J_TARGET=hosted` in `.env`
- ✅ Set `NEO4J_HOSTED_PASSWORD` in `.env`
- ✅ Set either `NEO4J_HOSTED_NAME` or `NEO4J_HOSTED_URI` in `.env`
- ✅ Restart backend/API

### "Cannot connect to backend"
- ✅ Check backend is running: `curl http://localhost:8000/health`
- ✅ Check BACKEND_URL in frontend sidebar
- ✅ Check firewall (if backend is on different machine)

### Neo4j Connection Timeout
- Check Neo4j Aura instance is running
- Verify credentials are correct
- Check network connectivity to neo4j+s:// endpoint

### "Module not found" errors
```bash
pip install -r requirements.txt
python -m uvicorn api:app --reload
```

---

## 📚 Next Steps

1. **Load Knowledge**: Ingest data using write mode
2. **Query Knowledge**: Ask questions in frontend chat
3. **Configure LLM**: Set OpenAI/Gemini for better extraction
4. **Deploy**: Use docker-compose in production
5. **Scale**: Multiple backend instances behind load balancer

---

## 📖 More Info

- [Full Integration Guide](FRONTEND_INTEGRATION.md)
- [Neo4j Setup Documentation](backend/docs/database/DOCKER_SETUP.md)
- [Backend Architecture](backend/docs/approach/)

---

**Ready?** Open http://localhost:8501 in your browser and start querying! 🧠
