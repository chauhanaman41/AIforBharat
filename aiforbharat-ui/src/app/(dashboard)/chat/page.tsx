"use client";

import { AssistantOverlay } from "@/components/chat/AssistantOverlay";
import { NlpToolbar } from "@/components/chat/NlpToolbar";

/**
 * AI Chat Page — Full-Page Assistant
 * =====================================
 * Phase 3: AI Chat & NLP Integration
 *
 * Layout:
 *  - Left (main): Full-height AssistantOverlay chat thread
 *  - Right (sidebar): NLP Tools (Translate, Summarize, Intent)
 *
 * Engines wired:
 *  - E0 Orchestrator: POST /query (RAG pipeline)
 *  - E7 Neural Network: POST /ai/chat, /ai/intent, /ai/translate, /ai/summarize
 *  - E6 Vector DB: POST /vectors/search (via orchestrator)
 *  - E0 Orchestrator: POST /voice-query
 *
 * Libraries: assistant-ui patterns, CopilotKit patterns, Gravity UI concepts
 */
export default function ChatPage() {
  return (
    <div className="flex gap-4 h-[calc(100vh-5rem)]">
      {/* Main Chat Thread */}
      <div className="flex-1 rounded-2xl border border-border/40 bg-card overflow-hidden shadow-sm">
        <AssistantOverlay />
      </div>

      {/* NLP Tools Sidebar */}
      <div className="hidden lg:flex flex-col w-[320px] gap-4">
        <NlpToolbar defaultExpanded />

        {/* Session Info Card */}
        <div className="rounded-xl border border-border/40 bg-card p-4 space-y-3">
          <h4 className="text-sm font-medium text-muted-foreground">About this Assistant</h4>
          <div className="space-y-2 text-xs text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Model</span>
              <span className="font-medium text-foreground">Llama 3.1 70B</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Runtime</span>
              <span className="font-medium text-foreground">NVIDIA NIM</span>
            </div>
            <div className="flex items-center justify-between">
              <span>RAG Pipeline</span>
              <span className="font-medium text-foreground">Orchestrator E0</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Vector Store</span>
              <span className="font-medium text-foreground">ChromaDB (E6)</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Data Location</span>
              <span className="font-medium text-foreground">Local Only</span>
            </div>
          </div>
          <div className="pt-2 border-t border-border/40">
            <p className="text-[10px] text-muted-foreground/60 leading-relaxed">
              All queries are processed locally through the orchestrator pipeline.
              Intent classification determines the routing path. Vector search
              retrieves relevant scheme passages for grounded answers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
