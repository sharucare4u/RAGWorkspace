"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, BrainCircuit } from "lucide-react";
import { Message, ChatResponse } from "@/lib/types";
import InsightCard from "@/components/InsightCard";
import EvidenceDrawer from "@/components/EvidenceDrawer";

const API_URL = "http://localhost:8000/api/chat";

function generateId(): string {
    return Math.random().toString(36).substring(2, 9);
}

export default function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Auto-scroll to bottom whenever messages change
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async () => {
        const query = input.trim();
        if (!query || isLoading) return;

        const userMsg: Message = {
            id: generateId(),
            role: "user",
            content: query,
        };

        const loadingMsg: Message = {
            id: generateId(),
            role: "assistant",
            content: "",
            isLoading: true,
        };

        setMessages((prev) => [...prev, userMsg, loadingMsg]);
        setInput("");
        setIsLoading(true);

        try {
            const res = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Server error");
            }

            const data: ChatResponse = await res.json();

            setMessages((prev) =>
                prev.map((m) =>
                    m.isLoading
                        ? {
                            ...m,
                            isLoading: false,
                            content: data.response_text,
                            response: data,
                        }
                        : m
                )
            );
        } catch (error: unknown) {
            const errMsg =
                error instanceof Error ? error.message : "Unknown error occurred.";
            setMessages((prev) =>
                prev.map((m) =>
                    m.isLoading
                        ? {
                            ...m,
                            isLoading: false,
                            content: `⚠️ Error: ${errMsg}`,
                        }
                        : m
                )
            );
        } finally {
            setIsLoading(false);
            inputRef.current?.focus();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-950 text-gray-100 font-sans">
            {/* ── Header ── */}
            <header className="flex-shrink-0 flex items-center gap-3 px-6 py-4 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30">
                    <BrainCircuit className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h1 className="text-lg font-bold tracking-tight text-white">
                        HR Insight Assistant
                    </h1>
                    <p className="text-xs text-gray-400">
                        Powered by SQL + Vector RAG Pipeline
                    </p>
                </div>
            </header>

            {/* ── Message Area ── */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-4 text-center select-none">
                        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-violet-500/40">
                            <BrainCircuit className="w-10 h-10 text-white" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                What would you like to know?
                            </h2>
                            <p className="text-gray-400 text-sm max-w-md">
                                Ask me about employee hours, salaries, performance reviews, or
                                anything across your HR data.
                            </p>
                        </div>
                        <div className="flex flex-wrap gap-2 justify-center mt-2">
                            {[
                                "Who worked the most overtime last month?",
                                "Summarise Alice's performance reviews",
                                "Compare hours worked vs reviews for the IT team",
                            ].map((s) => (
                                <button
                                    key={s}
                                    onClick={() => {
                                        setInput(s);
                                        inputRef.current?.focus();
                                    }}
                                    className="text-xs px-3 py-1.5 rounded-full border border-gray-700 text-gray-400 hover:border-violet-500 hover:text-violet-300 transition-colors duration-200"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id}>
                        {msg.role === "user" ? (
                            /* User bubble */
                            <div className="flex justify-end">
                                <div className="max-w-[70%] bg-violet-600/80 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-lg text-sm leading-relaxed">
                                    {msg.content}
                                </div>
                            </div>
                        ) : (
                            /* Assistant bubble */
                            <div className="flex flex-col gap-3 max-w-[85%]">
                                {msg.isLoading ? (
                                    <div className="flex items-center gap-3 px-4 py-4 bg-gray-800/60 rounded-2xl rounded-tl-sm border border-gray-700/50 w-fit">
                                        <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
                                        <span className="text-sm text-gray-400 animate-pulse">
                                            Thinking…
                                        </span>
                                    </div>
                                ) : (
                                    <>
                                        {msg.response && (
                                            <InsightCard
                                                text={msg.content}
                                                intent={msg.response.intent}
                                                latency={msg.response.evidence.latency}
                                            />
                                        )}
                                        {!msg.response && (
                                            <div className="px-4 py-3 bg-gray-800/60 rounded-2xl border border-red-800/40 text-sm text-red-300">
                                                {msg.content}
                                            </div>
                                        )}
                                        {msg.response && (
                                            <EvidenceDrawer evidence={msg.response.evidence} intent={msg.response.intent} />
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                <div ref={bottomRef} />
            </div>

            {/* ── Input Bar ── */}
            <div className="flex-shrink-0 px-4 pb-6 pt-3 border-t border-gray-800 bg-gray-950">
                <div className="max-w-4xl mx-auto flex items-center gap-2 bg-gray-800 rounded-2xl px-4 py-2 shadow-xl border border-gray-700 focus-within:border-violet-500 transition-colors duration-200">
                    <input
                        ref={inputRef}
                        type="text"
                        className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 outline-none py-2"
                        placeholder="Ask about employees, hours, reviews…"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        autoFocus
                    />
                    <button
                        onClick={sendMessage}
                        disabled={isLoading || !input.trim()}
                        className="flex items-center justify-center w-9 h-9 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-md shadow-violet-500/30 hover:shadow-violet-500/50 hover:scale-105 active:scale-95"
                    >
                        {isLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-white" />
                        ) : (
                            <Send className="w-4 h-4 text-white" />
                        )}
                    </button>
                </div>
                <p className="text-center text-xs text-gray-600 mt-2">
                    Press <kbd className="px-1 py-0.5 bg-gray-800 rounded text-gray-500 text-xs">Enter</kbd> to send
                </p>
            </div>
        </div>
    );
}
