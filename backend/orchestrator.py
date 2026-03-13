"""
Orchestrator — adapted from main_framework.py.
Returns a structured dict instead of printing to console.

This version adds robust fallbacks so the API does not 500 when the
local LLM (Ollama/OpenAI-compatible) is unavailable. It tries the LLM
first and gracefully falls back to rule-based logic.
"""
import sys
import os
import time
from typing import Optional

# Ensure the POC root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from SQL.sql_retrieval import text_to_sql_pipeline
from Vector_DB.chat import query_vector_db
from Logs import logs


# ── OpenAI/Ollama Client ─────────────────────────────────────────────────────
def _build_client() -> OpenAI:
    """Construct an OpenAI client using env overrides when present."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/")
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")
    return OpenAI(base_url=base_url, api_key=api_key)


client = _build_client()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
#OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")


def _safe_llm(prompt: str, temperature: float = 0.1) -> Optional[str]:
    """Try an LLM call. On failure, return None instead of raising."""
    try:
        resp = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"   (LLM) Fallback engaged due to error: {e}")
        return None


# ── Router ─────────────────────────────────────────────────────────────────────
def _route_fallback(question: str) -> str:
    """Simple keyword-based router used when LLM is unavailable."""
    q = question.lower()
    sql_kw = [
        "hour", "overtime", "timesheet", "timesheets", "salary", "salaries",
        "pay", "rate", "rates", "count", "sum", "average", "avg", "median",
        "min", "max", "date", "week", "month", "year", "join", "group",
        "department", "gross", "net", "tax", "benefits"
    ]
    vec_kw = [
        "review", "reviews", "feedback", "performance", "summary",
        "summarise", "summarize", "opinion", "sentiment", "qualitative",
        "comment", "comments", "strength", "weakness"
    ]

    has_sql = any(w in q for w in sql_kw)
    has_vec = any(w in q for w in vec_kw)
    if has_sql and has_vec:
        return "BOTH"
    if has_vec:
        return "VECTOR"
    if has_sql:
        return "SQL"
    # Default to VECTOR since it’s safer (no DB dependency)
    return "VECTOR"


def decide_route(question: str) -> str:
    prompt = f"""
    You are an Intent Router. Classify the user query into ONE category.
    
    1. SQL: Questions about NUMBERS, HOURS, DATES, RATES, or TIMESHEETS.
    2. VECTOR: Questions about REVIEWS, FEEDBACK, OPINIONS, or TEXT SUMMARIES.
    3. BOTH: Questions asking for BOTH numbers AND qualitative feedback.
    
    User Query: "{question}"
    
    Output ONLY the category name: SQL, VECTOR, or BOTH.
    """
    choice = _safe_llm(prompt, temperature=0.1)
    if choice is None:
        route = _route_fallback(question)
        print(f"   (Router) LLM unavailable — keyword fallback → {route}")
        return route

    choice = choice.strip().upper()
    print(f"   (Router) Raw LLM output: '{choice}'")

    words = [w.strip(".,") for w in choice.split()]
    if "BOTH" in words:
        return "BOTH"
    if "VECTOR" in words:
        return "VECTOR"
    if "SQL" in words:
        return "SQL"
    print("   (Router) Could not parse response cleanly — defaulting to VECTOR")
    return "VECTOR"


# ── Decomposer ─────────────────────────────────────────────────────────────────
def decompose_query(complex_question: str):
    prompt = f"""
    You are a Query Decomposer. The user has asked a complex question that requires data from TWO sources:
    1. SQL Database (Employee hours, rates, project stats)
    2. Vector Database (Performance reviews, qualitative feedback)
    
    User Question: "{complex_question}"
    
    Task: Break this into two separate, standalone questions.
    - The SQL question should ask ONLY for the specific numbers/stats mentioned.
    - The Vector question should ask ONLY for the qualitative review/feedback mentioned.
    
    Output Format:
    SQL: [Insert SQL-focused question]
    VECTOR: [Insert Vector-focused question]
    """
    result = _safe_llm(prompt, temperature=0.1)

    if result:
        sql_q, vector_q = "", ""
        for line in result.split('\n'):
            if line.startswith("SQL:"):
                sql_q = line.replace("SQL:", "").strip()
            elif line.startswith("VECTOR:"):
                vector_q = line.replace("VECTOR:", "").strip()
        if not sql_q:
            sql_q = complex_question
        if not vector_q:
            vector_q = complex_question
        return sql_q, vector_q

    # Fallback: simple heuristics
    return complex_question, complex_question


# ── Synthesizer ────────────────────────────────────────────────────────────────
def synthesize_answer(user_input: str, final_context: str) -> str:
    synth_prompt = f"""
    You are an HR Insight Assistant. Answer the user's question using the data retrieved from both SQL and Vector databases.
    
    User Question: {user_input}
    
    Data Retrieved:
    {final_context}
    
    Instructions:
    - Use the SQL data for any numeric insights (hours, rates, project stats).
    - Use the Vector data for any qualitative insights (reviews, feedback).
    - If the user asked for a comparison, explicitly compare the numbers with the text insights.
    - Always provide a clear, concise answer that directly addresses the user's original question.
    - Avoid repeating the data; instead, synthesize it into actionable insights or conclusions.
    - Provide a final recommendation if the data suggests one.
    - Always print the tables used and their column names if any retrieved from SQL, and the documents retrieved from the vector DB if any, as source of evidence.
    - Be concise and professional.
    - Use markdown formatting (bold, lists, tables) for clarity.
    """
    out = _safe_llm(synth_prompt, temperature=0.7)
    if out is not None:
        return out

    # Fallback: deterministic, template-based synthesis
    preview = (final_context or "No context available.").strip()
    if len(preview) > 800:
        preview = preview[:800] + "\n… [truncated]"
    return (
        "Answer (fallback)\n\n"
        "- This response was generated without an LLM because the local model endpoint was not reachable.\n"
        f"- User question: {user_input}\n\n"
        "Context used:\n"
        f"{preview}\n\n"
        "Notes:\n- Numeric facts reflect SQL data when present.\n- Text insights reflect vector search results when present.\n"
    )


# ── Main Entry Point ───────────────────────────────────────────────────────────
def process_query(query: str) -> dict:
    """
    Process a user query through the RAG pipeline.
    Returns a structured dict compatible with ChatResponse Pydantic model.
    """
    start_time = time.time()

    # 1. Route
    intent = decide_route(query)
    print(f"\n{'='*40}")
    print(f"  ROUTER DECISION: {intent}")
    print(f"  Query: '{query[:80]}{'...' if len(query) > 80 else ''}'")
    print(f"{'='*40}")

    # Evidence containers
    sql_query_str = None
    sql_columns = None
    sql_table = None
    vector_context = None
    vector_sources = None
    final_context_for_llm = ""

    # 2. Execute
    if intent == "SQL":
        sql_data = text_to_sql_pipeline(query)
        sql_query_str = sql_data.get("sql_query")
        sql_columns = sql_data.get("columns")
        sql_table = sql_data.get("rows")
        # Build text context for synthesizer
        if sql_columns and sql_table:
            rows_text = "\n".join(str(row) for row in sql_table)
            final_context_for_llm = f"Columns: {sql_columns}\nData:\n{rows_text}"
        else:
            final_context_for_llm = sql_data.get("error", "No data returned.")

    elif intent == "VECTOR":
        vec_data = query_vector_db(query)
        vector_context = vec_data.get("context")
        vector_sources = vec_data.get("sources")
        final_context_for_llm = vector_context or "No context found."

    elif intent == "BOTH":
        sql_sub_q, vector_sub_q = decompose_query(query)

        sql_data = text_to_sql_pipeline(sql_sub_q)
        sql_query_str = sql_data.get("sql_query")
        sql_columns = sql_data.get("columns")
        sql_table = sql_data.get("rows")

        vec_data = query_vector_db(vector_sub_q)
        vector_context = vec_data.get("context")
        vector_sources = vec_data.get("sources")

        sql_text = ""
        if sql_columns and sql_table:
            sql_text = f"Columns: {sql_columns}\nData:\n" + "\n".join(str(r) for r in sql_table)
        else:
            sql_text = sql_data.get("error", "No SQL data.")

        final_context_for_llm = (
            f"--- NUMERIC DATA (SQL) ---\n{sql_text}\n\n"
            f"--- PERFORMANCE REVIEWS (TEXT) ---\n{vector_context or 'No vector data.'}"
        )

    # 3. Synthesize
    response_text = synthesize_answer(query, final_context_for_llm)

    # 4. Log the interaction to PostgreSQL (mirrors main_framework.py behaviour)
    logs.log_interaction(
        query=query,
        intent=intent,
        tool="Hybrid" if intent == "BOTH" else intent,
        context=final_context_for_llm,
        response=response_text,
        start_time=start_time
    )

    latency = round(time.time() - start_time, 2)

    return {
        "response_text": response_text,
        "intent": intent,
        "evidence": {
            "sql_query": sql_query_str,
            "sql_columns": sql_columns,
            "sql_table": sql_table,
            "vector_context": vector_context,
            "vector_sources": vector_sources,
            "latency": latency,
        }
    }
