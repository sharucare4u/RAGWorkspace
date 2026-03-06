import psycopg2
from openai import OpenAI

# --- CONFIGURATION ---
DB_CONFIG = {
    "dbname": "poc",
    "user": "postgres",
    "password": "",  # <--- REPLACE THIS
    "host": "localhost",
    "port": "5432"
}

client = OpenAI(base_url="http://127.0.0.1:1234/v1/", api_key="lm-studio")

def execute_sql(query):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)
        colnames = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        return colnames, results
    except Exception as e:
        return None, str(e)
    finally:
        if conn: conn.close()

def text_to_sql_pipeline(user_question):
    """
    Converts natural language to SQL, runs it, and returns a structured dict.
    Returns: { "sql_query": str, "columns": list|None, "rows": list|None, "error": str|None }
    """
    print(f"   (SQL Tool) Thinking about: '{user_question}'...")

    prompt = f"""
    You are a SQL Assistant. Convert the user's question into a PostgreSQL query.
    
    Database Schema (Table: timesheets):
    - timesheet_id
    - emp_id
    - week_ending_date
    - hours_worked
    - overtime_hours
    - projects_worked
    - status

    Database Schema (Table: employees):
    - emp_id
    - full_name
    - role
    - department
    - manager_name
    - date_joined
    - email
    - annual_salary
    - is_active

    emp_id is the primary key in employees and a foreign key in timesheets.

    RULES:
    1. Return ONLY the SQL query. No markdown, no explanations.
    2. Do not write complex SQL queries if the question is simple. Always prefer simplicity.
    3. Use valid PostgreSQL syntax.
    4. Use join to combine tables if needed.
    5. If questions are asked about departments/roles always group them.
    
    User Question: {user_question}
    """
    
    try:
        response = client.chat.completions.create(
            model="mistral-7b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        sql_query = response.choices[0].message.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        print(f"   (SQL Tool) Executing: {sql_query}")
        columns, data = execute_sql(sql_query)
        
        if columns is None:
            # data is the error string when columns is None
            return {"sql_query": sql_query, "columns": None, "rows": None, "error": f"SQL Error: {data}"}
        elif not data:
            return {"sql_query": sql_query, "columns": columns, "rows": [], "error": "Query returned no data."}
        else:
            # Convert tuples to lists so the result is JSON-serialisable
            rows = [list(row) for row in data]
            return {"sql_query": sql_query, "columns": columns, "rows": rows, "error": None}

    except Exception as e:
        return {"sql_query": "", "columns": None, "rows": None, "error": f"Error communicating with LM Studio: {e}"}

# --- TEST BLOCK (Only runs if you run this file directly) ---
if __name__ == "__main__":
    print("--- SQL TOOL TEST MODE ---")
    while True:
        q = input("SQL Query: ")
        if q == "exit": break
        result = text_to_sql_pipeline(q)
        if result["error"]:
            print(f"Error: {result['error']}")
        else:
            print(f"SQL: {result['sql_query']}")
            print(f"Columns: {result['columns']}")
            for row in result["rows"]:
                print(row)
