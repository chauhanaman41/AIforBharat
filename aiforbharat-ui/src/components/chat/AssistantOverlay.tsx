"use client";

import { useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Trash2, Bot, Sparkles } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { PromptBar } from "./PromptBar";
import { useChatSession } from "@/hooks/use-chat";

/**
 * AssistantOverlay — Main AI Chat Thread
 * =========================================
 * assistant-ui inspired conversational thread component.
 * Features:
 *  - Auto-scrolling message list with smooth scroll
 *  - Empty state with onboarding prompts
 *  - PromptBar input with language selector
 *  - Clear conversation action
 *  - Session persistence across component mounts
 *
 * Component mapping: `AssistantOverlay.tsx` → assistant-ui + CopilotKit patterns
 * Libraries: assistant-ui concepts, ShadCN ScrollArea, Framer Motion
 */

interface AssistantOverlayProps {
  className?: string;
  compact?: boolean;
  showHeader?: boolean;
}

export function AssistantOverlay({
  className = "",
  compact = false,
  showHeader = true,
}: AssistantOverlayProps) {
  const { messages, isThinking, sendMessage, clearChat, sessionId } = useChatSession();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleSend = useCallback(
    (message: string) => {
      sendMessage(message);
    },
    [sendMessage]
  );

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      {showHeader && (
        <>
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl
                              bg-gradient-to-br from-chart-1 to-chart-3 text-white shadow-md">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">AIforBharat Assistant</h3>
                <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <span className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
                  Online · Local NIM Engine
                </p>
              </div>
            </div>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearChat}
                className="h-8 text-xs text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5 mr-1" />
                Clear
              </Button>
            )}
          </div>
          <Separator />
        </>
      )}

      {/* Message Thread */}
      <ScrollArea
        ref={scrollRef}
        className={`flex-1 ${compact ? "px-3 py-3" : "px-4 py-4"}`}
      >
        {messages.length === 0 ? (
          <EmptyState compact={compact} onSuggest={handleSend} />
        ) : (
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isLast={i === messages.length - 1}
              />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </ScrollArea>

      {/* Input */}
      <div className={`border-t border-border/40 ${compact ? "p-3" : "p-4"}`}>
        <PromptBar
          onSend={handleSend}
          isLoading={isThinking}
          showSuggestions={messages.length === 0 && !compact}
          compact={compact}
        />
      </div>
    </div>
  );
}

// ── Empty State ─────────────────────────────────────────────────────────────

function EmptyState({
  compact,
  onSuggest,
}: {
  compact?: boolean;
  onSuggest: (msg: string) => void;
}) {
  const suggestions = [
    { text: "What schemes am I eligible for?", emoji: "🎯" },
    { text: "Explain the PM Kisan Yojana", emoji: "🌾" },
    { text: "How to apply for Ayushman Bharat?", emoji: "🏥" },
    { text: "Check upcoming deadlines", emoji: "⏰" },
  ];

  if (compact) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl
                        bg-gradient-to-br from-chart-1/20 to-chart-3/20 mb-3">
          <Sparkles className="h-6 w-6 text-chart-1" />
        </div>
        <p className="text-sm text-muted-foreground">Ask me anything about government schemes</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center h-full py-12 text-center"
    >
      {/* Logo */}
      <div className="relative mb-6">
        <div className="flex h-16 w-16 items-center justify-center rounded-3xl
                        bg-gradient-to-br from-chart-1 to-chart-3 text-white shadow-xl">
          <Bot className="h-8 w-8" />
        </div>
        <div className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-green-500 border-2 border-background" />
      </div>

      <h3 className="text-lg font-semibold mb-1">AIforBharat Assistant</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-sm">
        Your personal civic AI. Ask about government schemes, eligibility,
        deadlines, and get answers powered by Llama 3.1 70B running locally.
      </p>

      {/* Onboarding Suggestions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
        {suggestions.map((s) => (
          <button
            key={s.text}
            onClick={() => onSuggest(s.text)}
            className="flex items-center gap-2 rounded-xl border border-border/60 bg-muted/30
                       px-4 py-3 text-left text-sm text-muted-foreground
                       hover:bg-accent hover:text-accent-foreground hover:border-accent
                       transition-all duration-200 hover:shadow-sm"
          >
            <span className="text-lg">{s.emoji}</span>
            <span className="line-clamp-1">{s.text}</span>
          </button>
        ))}
      </div>

      <p className="mt-6 text-[10px] text-muted-foreground/40 flex items-center gap-1">
        <Sparkles className="h-3 w-3" />
        Powered by local NVIDIA NIM infrastructure
      </p>
    </motion.div>
  );
}
