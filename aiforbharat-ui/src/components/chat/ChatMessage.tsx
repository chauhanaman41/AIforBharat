"use client";

import React, { memo, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bot,
  User,
  Copy,
  Check,
  Globe,
  FileText,
  Shield,
  HelpCircle,
  Briefcase,
  BookOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Chip } from "@nextui-org/react";
import { Button } from "@/components/ui/button";
import type { ChatMessage as ChatMessageType } from "@/hooks/use-chat";

/**
 * ChatMessage — Individual message bubble
 * =========================================
 * Renders user/assistant messages with:
 *  - Markdown rendering (react-markdown + remark-gfm)
 *  - Intent classification badge (Gravity UI / AIKit style)
 *  - Source citations collapsible
 *  - Copy to clipboard
 *  - Framer Motion entrance animation
 *
 * Libraries: react-markdown, Hero UI Chip, Framer Motion, Lucide
 */

// ── Intent → Icon mapping (AIKit / Gravity UI style) ────────────────────────

const INTENT_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  eligibility: { icon: Shield, color: "success", label: "Eligibility" },
  eligibility_check: { icon: Shield, color: "success", label: "Eligibility" },
  scheme_query: { icon: BookOpen, color: "primary", label: "Scheme Info" },
  scheme_info: { icon: BookOpen, color: "primary", label: "Scheme Info" },
  policy: { icon: FileText, color: "secondary", label: "Policy" },
  complaint: { icon: HelpCircle, color: "warning", label: "Complaint" },
  deadline: { icon: Briefcase, color: "danger", label: "Deadline" },
  general: { icon: Sparkles, color: "default", label: "General" },
  greeting: { icon: Sparkles, color: "default", label: "Greeting" },
  translation: { icon: Globe, color: "primary", label: "Translation" },
};

function getIntentConfig(intent?: string) {
  if (!intent) return null;
  return INTENT_CONFIG[intent.toLowerCase()] || INTENT_CONFIG.general;
}

// ── Streaming Dot Animation ─────────────────────────────────────────────────

function StreamingDots() {
  return (
    <div className="flex items-center gap-1.5 py-2">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="h-2 w-2 rounded-full bg-primary/60"
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.1, 0.8] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  );
}

// ── Source Citations ─────────────────────────────────────────────────────────

function SourceCitations({ sources }: { sources: string[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-3 pt-3 border-t border-border/40">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <FileText className="h-3 w-3" />
        <span>{sources.length} source{sources.length > 1 ? "s" : ""}</span>
        {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>
      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="mt-2 space-y-1.5"
        >
          {sources.map((src, i) => (
            <div
              key={i}
              className="text-xs text-muted-foreground bg-muted/50 rounded-md px-3 py-2 line-clamp-2"
            >
              {src}
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

interface ChatMessageProps {
  message: ChatMessageType;
  isLast?: boolean;
}

export const ChatMessage = memo(function ChatMessage({ message, isLast }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const intentConfig = getIntentConfig(message.intent);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`group flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} ${isLast ? "mb-4" : ""}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 flex items-start pt-1 ${
          isUser ? "ml-2" : "mr-2"
        }`}
      >
        <div
          className={`flex h-8 w-8 items-center justify-center rounded-xl ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-gradient-to-br from-chart-1/80 to-chart-3/80 text-white shadow-md"
          }`}
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>
      </div>

      {/* Bubble */}
      <div
        className={`relative max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-muted/60 text-foreground rounded-tl-sm border border-border/30"
        }`}
      >
        {/* Intent Badge */}
        {!isUser && intentConfig && (
          <div className="mb-2">
            <Chip
              size="sm"
              variant="flat"
              color={intentConfig.color as "success" | "primary" | "secondary" | "warning" | "danger" | "default"}
              startContent={<intentConfig.icon className="h-3 w-3" />}
              className="text-[10px] h-5"
            >
              {intentConfig.label}
              {message.intentConfidence && (
                <span className="ml-1 opacity-60">
                  {Math.round(message.intentConfidence * 100)}%
                </span>
              )}
            </Chip>
          </div>
        )}

        {/* Content */}
        {message.isStreaming && !message.content ? (
          <StreamingDots />
        ) : (
          <div
            className={`prose prose-sm max-w-none ${
              isUser
                ? "prose-invert"
                : "dark:prose-invert"
            }`}
          >
            {isUser ? (
              <p className="m-0 text-sm leading-relaxed">{message.content}</p>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        )}

        {/* Language badge */}
        {!isUser && message.language && message.language !== "en" && (
          <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
            <Globe className="h-3 w-3" />
            <span>Detected: {message.language}</span>
          </div>
        )}

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCitations sources={message.sources} />
        )}

        {/* Copy button */}
        {!isUser && message.content && !message.isStreaming && (
          <div className="absolute -bottom-3 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 rounded-full bg-background shadow-sm border"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          </div>
        )}

        {/* Timestamp */}
        <div
          className={`mt-1 text-[10px] opacity-40 ${
            isUser ? "text-right" : "text-left"
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </motion.div>
  );
});
