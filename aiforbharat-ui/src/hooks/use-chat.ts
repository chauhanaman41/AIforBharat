"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
import type {
  ChatRequest,
  ChatResponse,
  RagRequest,
  RagResponse,
  IntentResponse,
  TranslateRequest,
  TranslateResponse,
  SummarizeRequest,
  SummarizeResponse,
  VoiceQueryRequest,
  VoiceQueryResponse,
  VectorSearchRequest,
  VectorSearchResult,
} from "@/types/api";

/**
 * AIforBharat — Chat & NLP React Query Hooks
 * =============================================
 * Hooks for all AI/NLP endpoints (Phase 3):
 *  - useAiChat        → POST /ai/chat  (E7: Neural Network)
 *  - useRagQuery      → POST /query    (E0: Orchestrator RAG pipeline)
 *  - useAiIntent      → POST /ai/intent (E7: Intent classification)
 *  - useAiTranslate   → POST /ai/translate (E7: Translation)
 *  - useAiSummarize   → POST /ai/summarize (E7: Summarization)
 *  - useVoiceQuery    → POST /voice-query  (E0: Orchestrator voice pipeline)
 *  - useVectorSearch  → POST /vectors/search (E6: Vector DB)
 *  - useChatSession   → Local state manager for conversation threads
 *
 * All calls → http://localhost:8000/api/v1
 * No AWS, no external services.
 */

// ── Chat Message Type (local state) ─────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  intent?: string;
  intentConfidence?: number;
  entities?: Record<string, string>;
  language?: string;
  sources?: string[];
  isStreaming?: boolean;
  latency_ms?: number;
}

// ── Direct AI Chat (E7) ─────────────────────────────────────────────────────

export function useAiChat() {
  return useMutation({
    mutationFn: async (data: ChatRequest) => {
      const res = await apiClient.post<{ data: ChatResponse }>("/ai/chat", data);
      return res.data.data;
    },
    onError: (error: Error) => {
      toast.error("AI Chat Error", { description: error.message });
    },
  });
}

// ── RAG Query (E0 Orchestrator) ─────────────────────────────────────────────

export function useRagQuery() {
  return useMutation({
    mutationFn: async (data: { user_id: string; message: string; session_id?: string; top_k?: number }) => {
      const res = await apiClient.post<{ data: RagResponse & { intent?: string; confidence?: number; session_id?: string; sources?: VectorSearchResult[]; degraded?: string[] } }>("/query", data);
      return res.data.data;
    },
    onError: (error: Error) => {
      toast.error("Query Error", { description: error.message });
    },
  });
}

// ── Intent Classification (E7) ──────────────────────────────────────────────

export function useAiIntent() {
  return useMutation({
    mutationFn: async (data: { message: string; user_id?: string }) => {
      const res = await apiClient.post<{ data: IntentResponse }>("/ai/intent", data);
      return res.data.data;
    },
  });
}

// ── Translation (E7) ────────────────────────────────────────────────────────

export function useAiTranslate() {
  return useMutation({
    mutationFn: async (data: TranslateRequest) => {
      const res = await apiClient.post<{ data: TranslateResponse }>("/ai/translate", data);
      return res.data.data;
    },
    onSuccess: () => {
      toast.success("Translation complete");
    },
    onError: (error: Error) => {
      toast.error("Translation failed", { description: error.message });
    },
  });
}

// ── Summarization (E7) ──────────────────────────────────────────────────────

export function useAiSummarize() {
  return useMutation({
    mutationFn: async (data: SummarizeRequest) => {
      const res = await apiClient.post<{ data: SummarizeResponse }>("/ai/summarize", data);
      return res.data.data;
    },
    onSuccess: () => {
      toast.success("Summary generated");
    },
    onError: (error: Error) => {
      toast.error("Summarization failed", { description: error.message });
    },
  });
}

// ── Voice Query (E0 Orchestrator) ───────────────────────────────────────────

export function useVoiceQuery() {
  return useMutation({
    mutationFn: async (data: VoiceQueryRequest) => {
      const res = await apiClient.post<{ data: VoiceQueryResponse }>("/voice-query", data);
      return res.data.data;
    },
    onError: (error: Error) => {
      toast.error("Voice query failed", { description: error.message });
    },
  });
}

// ── Vector Search (E6) ──────────────────────────────────────────────────────

export function useVectorSearch() {
  return useMutation({
    mutationFn: async (data: VectorSearchRequest) => {
      const res = await apiClient.post<{ data: { results: VectorSearchResult[] } }>("/vectors/search", data);
      return res.data.data.results;
    },
  });
}

// ── Chat Session Manager (Local Zustand-like state) ─────────────────────────

export function useChatSession() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [isThinking, setIsThinking] = useState(false);
  const user = useAppStore((s) => s.user);
  const ragQuery = useRagQuery();
  const intentQuery = useAiIntent();

  const sendMessage = useCallback(
    async (content: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsThinking(true);

      // Placeholder assistant message (streaming illusion)
      const assistantId = crypto.randomUUID();
      const placeholderMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, placeholderMsg]);

      try {
        // Step 1: Classify intent in parallel (non-blocking)
        const intentPromise = intentQuery.mutateAsync({
          message: content,
          user_id: user?.user_id,
        }).catch(() => null);

        // Step 2: Show "connecting to fallback" after 3s of waiting
        const fallbackTimer = setTimeout(() => {
          toast.info("Connecting to Edge Fallback...", {
            description: "The primary AI engine is taking longer than expected.",
            duration: 4000,
          });
        }, 3000);

        // Step 3: RAG query (orchestrator pipeline) — with explicit catch
        const ragResult = await ragQuery.mutateAsync({
          user_id: user?.user_id || "anonymous",
          message: content,
          session_id: sessionId,
        }).catch((err: Error) => {
          clearTimeout(fallbackTimer);
          throw new Error("Orchestrator pipeline failed: " + err.message);
        });

        clearTimeout(fallbackTimer);

        // Wait for intent
        const intentResult = await intentPromise;

        // Update assistant message with full response
        const finalMsg: ChatMessage = {
          id: assistantId,
          role: "assistant",
          content: ragResult.answer || ragResult.context_used?.join("\n") || "I couldn't find a relevant answer. Please try rephrasing your question.",
          timestamp: Date.now(),
          intent: intentResult?.intent,
          intentConfidence: intentResult?.confidence,
          entities: intentResult?.entities,
          language: intentResult?.language,
          sources: ragResult.context_used,
          isStreaming: false,
        };

        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? finalMsg : m))
        );

        // Update session ID if returned
        const result = ragResult as unknown as Record<string, unknown>;
        if (result.session_id) {
          setSessionId(result.session_id as string);
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: "Sorry, I'm having trouble connecting to the AI service. Please ensure the backend is running on localhost:8000.",
                  isStreaming: false,
                }
              : m
          )
        );
      } finally {
        setIsThinking(false);
      }
    },
    [sessionId, user, ragQuery, intentQuery]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(crypto.randomUUID());
  }, []);

  return {
    messages,
    sessionId,
    isThinking,
    sendMessage,
    clearChat,
    setMessages,
  };
}
