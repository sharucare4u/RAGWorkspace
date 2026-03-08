# HR RAG System - Implementation Guide

## Project Overview

This is a **Hybrid RAG (Retrieval Augmented Generation) System** that intelligently routes HR-related queries to either SQL databases or vector-based document search, or both. The system uses a cloud LLM (via Ollama) to understand intent and generate responses with evidence.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ChatInterface Component                              │  │
│  │ - User query input                                   │  │
│  │ - Real-time message display                          │  │
│  │ - Evidence drawer (SQL & Vector results)             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend API (FastAPI - Port 8000)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ POST /api/chat                                       │  │
│  │ ├─ Takes ChatRequest: { query: string }              │  │
│  │ └─ Returns ChatResponse: { response_text, intent,    │  │
│  │                           evidence }                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ Calls
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Module                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ process_query(user_question)                         │  │
│  │                                                      │  │
│  │ 1. decide_route() → SQL | VECTOR | BOTH              │  │
│  │ 2. If SQL or BOTH:    query_sql()                    │  │
│  │ 3. If VECTOR or BOTH: query_vector_db()              │  │
│  │ 4. Synthesize response via LLM                       │  │
│  │ 5. Return structured result                          │  │
│  └──────────────────────────────────────────────────────┘  │
└────┬────────────────────────────┬────────────────────────┬──┘
     │                            │                        │
     ▼                            ▼                        ▼
┌─────────────────┐        ┌─────────────────┐   ┌──────────────────┐
│   SQL Module    │        │  Vector Module  │   │  Ollama (LLM)    │
│ (PostgreSQL)    │        │   (ChromaDB)    │   │ Port: 11434      │
│ Port: 5432      │        │ Local Storage   │   │ gpt-oss:20b-cloud│
└─────────────────┘        └─────────────────┘   └──────────────────┘
```

---

## Core Components

### 1. **Intent Router** (`decide_route()`)
**Purpose**: Analyzes user question and classifies it into one of three categories.

**Categories**:
- **SQL**: Queries about numbers, hours, dates, rates, timesheets (structured data)
- **VECTOR**: Queries about reviews, feedback, opinions, text summaries (unstructured data)
- **BOTH**: Hybrid queries requiring both data types

**Process**:
1. Takes user question as input
2. Sends prompt to Ollama (`gpt-oss:20b-cloud`)
3. Parses LLM response for category keywords
4. Returns category classification

**Example**:
```
Input: "How many hours did John work last week?"
Output: "SQL" (asking for quantitative data)

Input: "What feedback did Sarah receive in her review?"
Output: "VECTOR" (asking for qualitative feedback)

Input: "What are John's total hours and review comments?"
Output: "BOTH" (asking for both types)
```

---

### 2. **SQL Module** (`text_to_sql_pipeline()`)
**Purpose**: Converts natural language queries into executable SQL and retrieves structured data.

**Database Schema**:

#### Table: `employees`
| Column | Type | Notes |
|--------|------|-------|
| emp_id | INT | PK |
| full_name | VARCHAR |  |
| role | VARCHAR |  |
| department | VARCHAR |  |
| manager_name | VARCHAR |  |
| date_joined | DATE |  |
| email | VARCHAR |  |
| annual_salary | DECIMAL |  |
| is_active | BOOLEAN |  |

#### Table: `timesheets`
| Column | Type | Notes |
|--------|------|-------|
| timesheet_id | INT | PK |
| emp_id | INT | FK → employees.emp_id |
| week_ending_date | DATE |  |
| hours_worked | DECIMAL |  |
| overtime_hours | DECIMAL |  |
| projects_worked | VARCHAR |  |
| status | VARCHAR |  |

**Process**:
1. Takes user question and database schema context
2. Sends to Ollama (`gpt-oss:20b-cloud`) to generate SQL query
3. Executes query against PostgreSQL (Port 5432)
4. Returns structured result: `{ sql_query, columns, rows, error }`

**Key Rules**:
- No complex subqueries or CTEs
- No window functions
- Date filters only applied if user explicitly requests a specific year
- Simple SELECT, WHERE, GROUP BY, ORDER BY

**Example Output**:
```json
{
  "sql_query": "SELECT full_name, SUM(hours_worked) as total_hours FROM employees JOIN timesheets ON employees.emp_id = timesheets.emp_id GROUP BY full_name",
  "columns": ["full_name", "total_hours"],
  "rows": [["John Doe", 160], ["Jane Smith", 155]],
  "error": null
}
```

---

### 3. **Vector Module** (`query_vector_db()`)
**Purpose**: Performs semantic search over embedded documents using ChromaDB.

**Data Source**: Local ChromaDB instance at `chroma_db_local/`

**Embedding Model**: `all-MiniLM-L6-v2` (HuggingFace)

**Process**:
1. Takes user query as input
2. Converts query to embedding using HuggingFace model
3. Searches ChromaDB for top 5 most similar documents
4. Extracts document content and metadata
5. Returns: `{ context: str, sources: list[str] }`

**Example Output**:
```json
{
  "context": "John received excellent feedback on his project management skills...\n---\nHis communication was clear and effective...",
  "sources": ["performance_review_2025.pdf", "360_feedback_john.txt"]
}
```

---

### 4. **Orchestrator** (`process_query()`)
**Purpose**: Coordinates the entire query flow and synthesizes responses.

**Process Flow**:
```
1. decide_route(question)
   ├─ Result: "SQL" | "VECTOR" | "BOTH"
   │
2. Based on route:
   ├─ If "SQL":    Execute text_to_sql_pipeline()
   ├─ If "VECTOR": Execute query_vector_db()
   ├─ If "BOTH":   Execute both in parallel
   │
3. Aggregate results into evidence object
   
4. Use LLM to synthesize final response
   ├─ Input: Original question + evidence data
   └─ Output: Natural language answer
   
5. Return structured response:
   {
     "response_text": "...",
     "intent": "SQL" | "VECTOR" | "BOTH",
     "evidence": {
       "sql_query": "...",
       "sql_columns": [...],
       "sql_table": [...],
       "vector_context": "...",
       "vector_sources": [...],
       "latency": 1.23
     }
   }
```

---

### 5. **FastAPI Backend** (`backend/main.py`)
**Purpose**: Provides REST API interface for frontend communication.

**Endpoint**:
```
POST /api/chat
Content-Type: application/json

{
  "query": "How many hours has John worked in 2025?"
}

Response:
{
  "response_text": "John worked a total of 160 hours in 2025.",
  "intent": "SQL",
  "evidence": {
    "sql_query": "SELECT SUM(hours_worked) FROM timesheets...",
    "sql_columns": ["total_hours"],
    "sql_table": [[160]],
    "vector_context": null,
    "vector_sources": null,
    "latency": 0.45
  }
}
```

**CORS Configuration**: Allows requests from `http://localhost:3000`

**Run Command**:
```bash
uvicorn backend/main:app --reload --port 8000
```

---

### 6. **Frontend** (Next.js - Port 3000)
**Purpose**: User interface for interacting with the RAG system.

**Key Components**:

#### `ChatInterface.tsx`
- Main chat component
- Message history display
- Query input field
- Real-time loading states
- Calls `/api/chat` endpoint

#### `EvidenceDrawer.tsx`
- Displays SQL results in table format
- Shows vector search results and sources
- Collapsible drawer for evidence inspection

#### `InsightCard.tsx`
- Formats and displays AI-generated response
- Shows metadata (intent, latency)

**Run Command**:
```bash
cd frontend
npm run dev
# Runs on http://localhost:3000
```

---

## Implementation Workflow

### Phase 1: Setup & Prerequisites
1. **PostgreSQL Database**
   - Create and populate `employees` and `timesheets` tables
   - Test connectivity on Port 5432
   - Verify schema matches SQL module expectations

2. **ChromaDB Vector Store**
   - Initialize at `chroma_db_local/`
   - Use `store_documents.py` to embed and store HR documents
   - Verify embeddings are searchable

3. **Ollama**
   - Download and install Ollama from [ollama.com](https://ollama.com/download)
   - Sign in to your Ollama account: `ollama signin`
   - Pull the cloud model: `ollama pull gpt-oss:20b-cloud`
   - Ollama serves the OpenAI-compatible API automatically at `http://localhost:11434/v1/`

### Phase 2: Backend Setup
1. **Configure environment** in `SQL/sql_retrieval.py`:
   ```python
   DB_CONFIG = {
       "dbname": "poc",
       "user": "postgres",
       "password": "your_password",  # ← Update this
       "host": "localhost",
       "port": "5432"
   }
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements_backend.txt
   # FastAPI, Pydantic, psycopg2, chromadb, langchain, openai
   ```

3. **Start FastAPI server**:
   ```bash
   uvicorn backend/main:app --reload --port 8000
   ```
   - Test health: `curl http://localhost:8000/docs` (Swagger UI)

### Phase 3: Frontend Setup
1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```
   - Opens on `http://localhost:3000`

### Phase 4: End-to-End Testing
1. Ask SQL query: *"How many hours did John work?"*
   - Expected: SQL route, results in table, sources shown

2. Ask Vector query: *"What feedback did John receive?"*
   - Expected: VECTOR route, relevant excerpts shown, sources listed

3. Ask hybrid query: *"What are John's total hours and feedback?"*
   - Expected: BOTH route, both SQL and Vector results shown

4. Verify latency and evidence accuracy

---

## Query Flow Examples

### Example 1: SQL Query
```
User Input: "How many hours did John work in January 2025?"

1. Router Analysis:
   → Query about NUMBERS and DATES → SQL

2. SQL Module:
   → Generates: SELECT SUM(hours_worked) FROM timesheets 
                WHERE emp_id = (SELECT emp_id FROM employees WHERE full_name = 'John')
                AND EXTRACT(MONTH FROM week_ending_date) = 1
                AND EXTRACT(YEAR FROM week_ending_date) = 2025
   → Executes against PostgreSQL
   → Returns: 168 hours

3. Response Synthesis:
   → LLM generates: "John worked 168 hours in January 2025."

4. Evidence Shown:
   - SQL Query executed
   - Query results in table format
   - Latency: 0.23s
```

### Example 2: Vector Query
```
User Input: "What were John's strengths mentioned in his review?"

1. Router Analysis:
   → Query about FEEDBACK and OPINIONS → VECTOR

2. Vector Module:
   → Converts query to embedding
   → Searches ChromaDB for similar documents (k=5)
   → Finds: performance_review_2025.pdf, 360_feedback.txt
   → Extracts relevant passages about strengths

3. Response Synthesis:
   → LLM generates: "According to his review, John excelled in project management, communication, and team collaboration..."

4. Evidence Shown:
   - Relevant excerpts from documents
   - Source files and metadata
   - Latency: 0.18s
```

### Example 3: Hybrid Query
```
User Input: "Show me John's total hours and manager feedback"

1. Router Analysis:
   → Query about both NUMBERS and FEEDBACK → BOTH

2. Execute in Parallel:
   a) SQL Module → Gets total hours (168)
   b) Vector Module → Finds manager feedback documents

3. Response Synthesis:
   → LLM combines both: "John has logged 168 hours total. His manager noted excellent leadership and communication skills..."

4. Evidence Shown:
   - Both SQL and Vector results
   - Combined latency: 0.35s
```

---

## Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Next.js 14, React, TypeScript | User interface |
| Backend | FastAPI, Python | REST API server |
| Intent Routing | Ollama + gpt-oss:20b-cloud | Intent classification |
| SQL Database | PostgreSQL | Structured HR data |
| Vector Store | ChromaDB | Semantic document search |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) | Convert text to vectors |
| LLM | gpt-oss:20b-cloud (Ollama) | Text generation & analysis |

---

## File Structure Reference

```
POC/
├── main_framework.py          # Original framework (reference)
├── requirements.txt            # Root dependencies
├── create_audit.py             # Audit creation utility
├── .gitignore                  # Git ignore rules
│
├── backend/
│   ├── main.py                # FastAPI application
│   ├── orchestrator.py        # Query orchestration logic
│   └── requirements_backend.txt # Backend dependencies
│
├── frontend/
│   ├── package.json            # Node dependencies
│   ├── next.config.ts          # Next.js configuration
│   ├── tsconfig.json           # TypeScript config
│   ├── app/
│   │   ├── layout.tsx          # App layout
│   │   ├── page.tsx            # Home page
│   │   └── globals.css         # Global styles
│   └── components/
│       ├── ChatInterface.tsx   # Main chat component
│       ├── EvidenceDrawer.tsx  # Evidence display
│       └── InsightCard.tsx     # Response card
│
├── SQL/
│   ├── sql_retrieval.py        # SQL query generation & execution
│   ├── create_tables.py        # Database schema setup
│   └── __init__.py
│
├── Vector_DB/
│   ├── chat.py                 # Vector search logic
│   ├── store_documents.py      # Document ingestion
│   ├── document_gen.py         # Document generation
│   └── __init__.py
│
├── Logs/
│   ├── logs.py                 # Logging utilities
│   └── __init__.py
│
├── chroma_db_local/            # Local vector database
│   └── chroma.sqlite3
│
└── performance_reviews/        # Sample HR documents
```

---

## Troubleshooting Guide

### Issue: Frontend can't reach backend
- **Check**: `backend/main.py` is running on port 8000
- **Fix**: Verify CORS origin: `http://localhost:3000`
- **Command**: `curl http://localhost:8000/docs`

### Issue: PostgreSQL connection error
- **Check**: DB credentials in `SQL/sql_retrieval.py`
- **Check**: PostgreSQL is running on port 5432
- **Test**: `psql -h localhost -U postgres -d poc`

### Issue: Ollama not responding
- **Check**: Ollama is running (`ollama serve` or check system tray)
- **Check**: You are signed in — run `ollama signin`
- **Check**: Model is pulled — run `ollama pull gpt-oss:20b-cloud`
- **Test**: `curl http://localhost:11434/v1/models`

### Issue: Vector search returns no results
- **Check**: ChromaDB exists at `chroma_db_local/`
- **Check**: Documents are embedded and stored
- **Run**: `python Vector_DB/store_documents.py` to index documents

---

## Performance Optimization Tips

1. **Parallel Query Execution**: For "BOTH" queries, run SQL and Vector in parallel threads
2. **Query Caching**: Cache frequent queries to reduce LLM calls
3. **Index Optimization**: Add database indexes on frequently searched columns (emp_id, week_ending_date)
4. **ChromaDB Tuning**: Adjust `k=5` in similarity search based on result quality
5. **LLM Temperature**: Keep at 0.1 for consistent SQL generation, 0.3-0.5 for varied responses
6. **Batch Processing**: Process multiple queries together for better throughput

---

## Next Steps & Future Enhancements

1. **Authentication**: Add user login and role-based access control
2. **Query History**: Store and allow users to search previous queries
3. **Multi-turn Conversation**: Implement session management for follow-up questions
4. **Export Functionality**: Allow users to export SQL results and evidence as PDF
5. **Analytics Dashboard**: Track query patterns and system performance
6. **Advanced Filtering**: Add date range, department filters to UI
7. **Mobile Support**: Responsive design for mobile devices
8. **Model Upgrades**: Swap to a larger Ollama cloud model (e.g., `gpt-oss:120b-cloud`) for higher accuracy

---

## Support & Monitoring

- **System Logs**: Check `Logs/logs.py` for application logging
- **Database Logs**: Monitor PostgreSQL query logs
- **Vector DB Monitoring**: Track ChromaDB query performance
- **API Metrics**: Monitor FastAPI latency via built-in metrics
- **Frontend Errors**: Check browser console for client-side errors

