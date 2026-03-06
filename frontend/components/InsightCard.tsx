"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Database, FileText, Layers, Clock } from "lucide-react";

interface InsightCardProps {
    text: string;
    intent: "SQL" | "VECTOR" | "BOTH";
    latency: number;
}

const intentConfig = {
    SQL: {
        icon: Database,
        label: "SQL",
        color: "text-blue-400",
        bg: "bg-blue-500/10",
        border: "border-blue-500/30",
    },
    VECTOR: {
        icon: FileText,
        label: "Vector",
        color: "text-emerald-400",
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/30",
    },
    BOTH: {
        icon: Layers,
        label: "Hybrid",
        color: "text-violet-400",
        bg: "bg-violet-500/10",
        border: "border-violet-500/30",
    },
};

export default function InsightCard({ text, intent, latency }: InsightCardProps) {
    const cfg = intentConfig[intent];
    const Icon = cfg.icon;

    return (
        <div className="bg-gray-800/60 rounded-2xl rounded-tl-sm border border-gray-700/50 overflow-hidden shadow-lg">
            {/* Badge row */}
            <div className="flex items-center gap-2 px-4 pt-3 pb-2">
                <span
                    className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.border} ${cfg.color}`}
                >
                    <Icon className="w-3 h-3" />
                    {cfg.label}
                </span>
                <span className="ml-auto flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    {latency}s
                </span>
            </div>

            {/* Markdown content */}
            <div className="px-4 pb-4">
                <div className="prose prose-invert prose-sm max-w-none
          prose-p:text-gray-200 prose-p:leading-relaxed
          prose-headings:text-white prose-headings:font-semibold
          prose-strong:text-white
          prose-code:text-violet-300 prose-code:bg-gray-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
          prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-700
          prose-ul:text-gray-200 prose-li:text-gray-200
          prose-a:text-violet-400">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
