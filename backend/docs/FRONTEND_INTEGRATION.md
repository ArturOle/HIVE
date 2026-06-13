# Frontend Integration Guide

## Overview

The frontend has been updated to support multi-message conversations with the backend orchestrator. It now communicates with a new HTTP API server that wraps the `AgentOrchestrator`, enabling seamless read-mode queries.

## Architecture

```
Frontend (Streamlit)
    ↓ HTTP/REST
Backend API Server (FastAPI)
    ↓ Python
Orchestrator (LangGraph)
    ↓
Database & LLM Providers
```

## Setup

### 1. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` in the project root with your Neo4j credentials.

#### Option A: Hosted Neo4j (Neo4j Aura) - Recommended for Production

```env
# Neo4j Target
NEO4J_TARGET=hosted

# Neo4j Aura Credentials (get from https://neo4j.com/cloud/aura/)
NEO4J_HOSTED_NAME=your-instance-id      # e.g., "97f8db06"
NEO4J_HOSTED_PASSWORD=your-password      # From Aura console

# Optional
NEO4J_HOSTED_URI=neo4j+s://instance.databases.neo4j.io  # Auto-generated if using NAME
NEO4J_HOSTED_USERNAME=neo4j              # Default: neo4j
NEO4J_HOSTED_DATABASE=neo4j              # Default: neo4j

# LLM Provider (optional)
LLM_PROVIDER=openai  # or gemini
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

#### Option B: Local Neo4j (For Development)

```env
# Neo4j Target
NEO4J_TARGET=local

# Local Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM Provider (optional)
LLM_PROVIDER=none
```

### 3. Start Services

#### Option A: Using the convenience script (Linux/Mac)

```bash
chmod +x start_services.sh
./start_services.sh
```

This will:
1. Start the backend API on `http://localhost:8000` (connects to Neo4j Aura or local)
2. Wait for the backend to be ready
3. Start the frontend on `http://localhost:8501`

#### Option B: Docker Compose (Hosted Neo4j)

For hosted Neo4j (recommended for production):

```bash
# With hosted Neo4j from Aura (uses .env variables)
docker-compose up -d

# Then open:
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
```

#### Option C: Docker Compose (Local Neo4j)

For development with local Docker Neo4j:

```bash
# Start with local Neo4j profile
docker-compose --profile local up -d

# Then open:
# Frontend: http://localhost:8501
# Neo4j Browser: http://localhost:7474 (user: neo4j, password: password)
```

#### Option D: Manual startup

**Terminal 1 - Backend API:**
```bash
cd backend
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
BACKEND_URL=http://localhost:8000 streamlit run src/main.py
```

## Usage

### Frontend Interface

1. **Main Chat Area**: Display of conversation history with user and assistant messages
2. **Input Bar**: Type your query and press Enter to send
3. **Sidebar Controls**:
   - **Backend URL**: Configure the backend API endpoint
   - **Top-K Results**: Control how many results are retrieved (1-50)
   - **Clear Conversation**: Reset the chat history

### Example Workflow

1. Open the frontend at `http://localhost:8501`
2. Ask a question: *"How do I handle motor overheat?"*
3. The frontend sends it to the backend in read mode
4. The orchestrator retrieves relevant knowledge and returns results
5. Results are formatted and displayed in the chat interface
6. Continue the multi-message conversation

## API Endpoints

### Health Check
```
GET /health
```
Response: `{"status": "ok"}`

### Read Query
```
POST /read
Content-Type: application/json

{
  "query": "How to fix...",
  "top_k": 5  # optional
}
```

Response:
```json
{
  "data": {
    "query": "...",
    "response": {...},
    "ranked": [...],
    "errors": []
  }
}
```

### Write Query
```
POST /write
Content-Type: application/json

{
  "text": "New knowledge...",
  "environment_hint": "general"  # optional
}
```

## Frontend Components

### `format_backend_response(response)`
Converts backend response to readable Markdown format. Handles:
- Structured responses with summary, details, results
- Raw JSON data
- Error cases

### `query_backend(query, top_k)`
Async HTTP client that:
- Connects to backend API
- Handles timeouts and connection errors
- Returns parsed JSON response

### Message Management
- Maintains conversation history in `st.session_state.messages`
- Stores both user and assistant messages
- Persists across Streamlit reruns

## Error Handling

The frontend gracefully handles:

1. **Connection Error**: Backend not running or unreachable
   - Display: "Cannot connect to backend"
   - User can adjust Backend URL in sidebar

2. **Timeout Error**: Backend taking too long
   - Display: "Backend request timed out"
   - Timeout: 60 seconds (configurable)

3. **HTTP Error**: Backend returned an error
   - Display: Error message from backend
   - Logged for debugging

## Configuration

### Adjust Request Timeout
Edit `frontend/src/main.py`:
```python
REQUEST_TIMEOUT = 60.0  # seconds
```

### Customize Backend URL
Environment variable:
```bash
export BACKEND_URL=http://your-backend-host:8000
streamlit run src/main.py
```

Or use the sidebar input field during runtime.

### Change Response Formatting
Modify `format_backend_response()` to customize how backend results are displayed.

## Troubleshooting

### Frontend Can't Connect to Backend
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `BACKEND_URL` in sidebar matches backend host:port
3. Check firewall rules if backend is remote

### Hosted Neo4j Connection Issues
1. **Credentials not configured**: Check .env has `NEO4J_HOSTED_PASSWORD` and `NEO4J_HOSTED_NAME`
2. **Invalid credentials**: Verify instance ID and password from Neo4j Aura console
3. **Connection timeout**: Check Neo4j Aura instance is running and network connectivity
4. **Check logs**: `docker-compose logs backend_api` or backend terminal output

### Slow Responses
1. Check backend logs for performance issues
2. Reduce `top_k` value for faster retrieval
3. Monitor Neo4j Aura performance dashboard

### Conversation Not Persisting
This is expected! Messages are stored in browser session memory and clear on page refresh. To persist:
- Add database backing to `st.session_state`
- Implement message storage in backend

## Next Steps

### Future Enhancements
1. **Conversation Persistence**: Store messages in database
2. **Export Conversations**: Download chat as markdown/PDF
3. **Message Editing**: Allow user to edit/retry previous messages
4. **Streaming Responses**: Show backend output in real-time
5. **Authentication**: Add user login/sessions
6. **Rate Limiting**: Implement query throttling

### Performance Optimization
1. Add response caching layer
2. Implement pagination for large result sets
3. Use WebSockets for real-time updates
4. Add response compression

## Architecture Diagram

```
┌─────────────────┐
│    Browser      │
│   (Streamlit)   │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   Frontend      │
│  (main.py)      │ - Chat history
│                 │ - Message formatting
└────────┬────────┘
         │ httpx.AsyncClient
         ↓
┌─────────────────┐
│  Backend API    │
│  (FastAPI)      │ - /health
└────────┬────────┘ - /read
         │          - /write
         ↓
┌─────────────────┐
│  Orchestrator   │
│  (LangGraph)    │ - Query parsing
└────────┬────────┘ - Concept extraction
         │          - Knowledge retrieval
         ↓
┌─────────────────┐
│   Neo4j DB      │
│ + LLM Provider  │
└─────────────────┘
```

## Support

For issues or questions:
1. Check backend logs: `python -m uvicorn api:app --reload`
2. Review frontend console: F12 in browser
3. Examine orchestrator behavior in backend/docs/
