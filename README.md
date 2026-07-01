# HIVE Mind service
|||
|-|-| 
| Last readme update | 29/06/2026 |
| Author | Artur "R2" Oleksiński | 

## About the project
**H**ierarchically **I**ndexed **V**ector **E**viroments(HIVE) is experimental agentic abstract memory system. HIVE mimics the high-level human resoning and memory recall strategies, recomposing the information into `expiriences`.

## Initial setup
### Option 1: Local shell-based setup
1. Start the local services from the repository root with `./start_services.sh`.
2. Install backend dependencies with `cd backend && pip install -e .`.
3. Launch the API or frontend as needed for your workflow.

### Option 2: Docker Compose setup
1. From the repository root, run `docker compose up --build`.
2. This starts the backend and supporting services defined in the compose configuration.
3. Use the exposed ports from the compose file to access the API or frontend once the containers are healthy.

## Orchestrator modes
- Submit: ingest new content, extract concepts and relations, and build or extend the underlying experience graph. This is the path used when you want to add new knowledge into HIVE.
- Retrieve: perform standard retrieval over stored experiences and return the most relevant context. It is the default flow for answering questions from the existing memory base.
- Advanced retrieve: an experimental multi-step graph exploration and reasoning flow. It expands the retrieval process by traversing related concepts and applying more structured reasoning, but it is still in development and may change over time.

## Development stages

### 1. Proof Of Concept - *Success*

**Goal:**
Impelement a simple, generic expirience extraction and retrieval from one domain, text document.

**Acceptance criterias:**
- Small local LLM can respond on similar level to document specific questions as frontier models.
- We are able to automatically create independent graphs for given topic together with all concepts.

### 2. Iteration 1 - Improvement of Retrieval procedures - *Ongoing*

**Goal:**
Prepare multi-step graph exploration retrieval. 
- First, extract concepts occuring in the user query.
- Second, Perform semantic search on eachindependent concept type.
- Third, return the target concept from realation eg. From HIVE-extracted similar problems as in user query, grab their results and deduplicate.

**Acceptance criteria:**
- Mesurably improved LLM results.
- Higher quelity of extracted information(even for mixed-domain entries in database).
- Full traceability of retrieval steps and data presented to LLM.

### 3. Iteration 2 - Introduce facts - *Planning*

**Goal:**

Up till this point system focuses on *expiriences*, problem-solution flow. This however will not cover the known truths about the world that we want to preserve or challange. Facts will be concrete, well established informations saved as the base for resoning.

Facts will be responsible to provide additional context to expiriences, allowing for fact-checking and resolving contradicting information, acting as a ground-truth.

Facts will be devided into soft and hard, one being the facts infered during memory consolidation process and second will be facts hard coded into the database.

For the whole process, entire memory and fact managment process will be necessary but for this iteration we just want to connect them to the existing expirience graphs and attach with extracted concepts.

**Acceptance criteria:**
- Fact node type exists
- Facts are connected with other concepts during extraction.
- Facts can be attached to the response as supplementary information.
- Facts partially covers holes of reasoning mechanic in current system.