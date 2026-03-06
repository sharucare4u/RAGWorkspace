import sys
import json
import time
from openai import OpenAI

# --- IMPORT TOOLS ---
try:
    from SQL import sql_retrieval
    from Vector_DB import chat
    from Logs import logs
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

client = OpenAI(base_url="http://127.0.0.1:1234/v1/", api_key="lm-studio")

# --- 1. THE ROUTER ---
def decide_route(question):
    print(f"\nRouter Analyzing: '{question}'...")
    
    prompt = f"""
    You are an Intent Router. Classify the user query into ONE category.
    
    1. SQL: Questions about NUMBERS, HOURS, DATES, RATES, or TIMESHEETS.
    2. VECTOR: Questions about REVIEWS, FEEDBACK, OPINIONS, or TEXT SUMMARIES.
    3. BOTH: Questions asking for BOTH numbers AND qualitative feedback.
    
    User Query: "{question}"
    
    Output ONLY the category name: SQL, VECTOR, or BOTH.
    """
    
    response = client.chat.completions.create(
        model="mistral-7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    choice = response.choices[0].message.content.strip().upper()
    
    if "BOTH" in choice: return "BOTH"
    if "SQL" in choice: return "SQL"
    return "VECTOR"

# --- 2. THE DECOMPOSER ---
def decompose_query(complex_question):
    """
    Breaks a hybrid question into two separate, optimized questions.
    """
    print("   (Decomposer) Splitting query...")
    
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
    
    response = client.chat.completions.create(
        model="mistral-7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    result = response.choices[0].message.content.strip()
    
    # Simple parsing logic
    sql_q = ""
    vector_q = ""
    
    for line in result.split('\n'):
        if line.startswith("SQL:"):
            sql_q = line.replace("SQL:", "").strip()
        elif line.startswith("VECTOR:"):
            vector_q = line.replace("VECTOR:", "").strip()
            
    # Fallback if parsing fails
    if not sql_q: sql_q = complex_question
    if not vector_q: vector_q = complex_question
    
    print(f"      -> SQL Query: {sql_q}")
    print(f"      -> Vector Query: {vector_q}")
    
    return sql_q, vector_q

# --- 3. THE ORCHESTRATOR ---
def run_orchestrator():
    print("Type 'exit' to quit.")
    
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit"]: break
        
        start_time = time.time() # <--- START TIMER
        
        # 1. ROUTE
        route = decide_route(user_input)
        print(f"DECISION: {route}")
        
        final_context = ""
        
        # 2. EXECUTE
        if route == "SQL":
            final_context = sql_retrieval.text_to_sql_pipeline(user_input)
            
        elif route == "VECTOR":
            final_context = chat.query_vector_db(user_input)
            
        elif route == "BOTH":
            print("   -> Running Hybrid Search (with Decomposition)...")
            
            # Step A: Decompose
            sql_sub_q, vector_sub_q = decompose_query(user_input)
            
            # Step B: Execute in Parallel (conceptually)
            sql_res = sql_retrieval.text_to_sql_pipeline(sql_sub_q)
            vec_res = chat.query_vector_db(vector_sub_q)
            
            # Step C: Aggregate
            final_context = f"--- NUMERIC DATA (SQL) ---\n{sql_res}\n\n--- PERFORMANCE REVIEWS (TEXT) ---\n{vec_res}"

        # 3. SYNTHESIZE FINAL ANSWER
        print("\n   (Synthesizer) Merging answers...")
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
        - Provide a final recommendation if the data suggests one (e.g., "Employee X is performing well based on their hours and positive reviews, but should focus on improving Y").
        - Always print the tables used and their column names if any retrieved from SQL, and the documents retrieved from the vector DB if any, as source of evidence.
        - Be concise and professional.
        """
        
        final_response_obj = client.chat.completions.create(
             model="mistral-7b-instruct",
             messages=[{"role": "user", "content": synth_prompt}],
             temperature=0.7
        )
        
        # Extract the actual text string
        final_answer_text = final_response_obj.choices[0].message.content.strip()

        # 4. LOGGING
        # Ensure we use the variables defined above: 'final_context' and 'final_answer_text'
        logs.log_interaction(
                query=user_input,
                intent=route,
                tool="Hybrid" if route == "BOTH" else route,
                context=final_context,    # <--- Fixed variable name
                response=final_answer_text, # <--- Fixed variable name
                start_time=start_time
            )

        print(f"\nFINAL ANSWER:\n{final_answer_text}")

if __name__ == "__main__":
    run_orchestrator()