// Shared TypeScript interfaces mirroring the FastAPI Pydantic response model

export interface Evidence {
    sql_query?: string | null;
    sql_columns?: string[] | null;
    sql_table?: (string | number | boolean | null)[][] | null;
    vector_context?: string | null;
    vector_sources?: string[] | null;
    latency: number;
}

export interface ChatResponse {
    response_text: string;
    intent: "SQL" | "VECTOR" | "BOTH";
    evidence: Evidence;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    response?: ChatResponse;
    isLoading?: boolean;
}
