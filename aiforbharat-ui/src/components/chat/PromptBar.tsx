"use client";

import { useState, useRef, useCallback } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Mic,
  MicOff,
  Loader2,
  Globe,
  Sparkles,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * PromptBar — Rich AI Input Component
 * ======================================
 * Prompt Kit / AIKit (Gravity UI) inspired input bar.
 * Features:
 *  - Auto-resizing textarea (react-textarea-autosize)
 *  - Language selector for multilingual input
 *  - Voice toggle (mic icon — visual only, wired to useVoiceQuery)
 *  - Suggestion chips with quick prompts
 *  - Gradient send button with loading state
 *
 * Libraries: react-textarea-autosize, Framer Motion, Lucide, ShadCN Select
 */

const QUICK_SUGGESTIONS = [
  { label: "Check my eligibility", icon: "🎯" },
  { label: "Explain PM Kisan scheme", icon: "🌾" },
  { label: "Upcoming deadlines", icon: "⏰" },
  { label: "Government schemes for women", icon: "👩" },
  { label: "How to apply for Ayushman Bharat", icon: "🏥" },
  { label: "Translate to Hindi", icon: "🗣️" },
];

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी" },
  { value: "bn", label: "বাংলা" },
  { value: "te", label: "తెలుగు" },
  { value: "mr", label: "मराठी" },
  { value: "ta", label: "தமிழ்" },
  { value: "gu", label: "ગુજરાતી" },
  { value: "kn", label: "ಕನ್ನಡ" },
  { value: "ml", label: "മലയാളം" },
  { value: "pa", label: "ਪੰਜਾਬੀ" },
  { value: "or", label: "ଓଡ଼ିଆ" },
  { value: "as", label: "অসমীয়া" },
];

interface PromptBarProps {
  onSend: (message: string, language?: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  showSuggestions?: boolean;
  compact?: boolean;
}

export function PromptBar({
  onSend,
  isLoading = false,
  placeholder = "Ask about government schemes, eligibility, deadlines...",
  showSuggestions = true,
  compact = false,
}: PromptBarProps) {
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [isListening, setIsListening] = useState(false);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed, language);
    setInput("");
    textareaRef.current?.focus();
  }, [input, language, isLoading, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (text: string) => {
    onSend(text, language);
  };

  const toggleVoice = () => {
    setIsListening(!isListening);
    // Voice recording is visual-only; actual transcription
    // would go through POST /voice-query after STT
    if (!isListening) {
      setTimeout(() => setIsListening(false), 5000);
    }
  };

  return (
    <div className="space-y-3">
      {/* Suggestion Chips */}
      {showSuggestions && !compact && !input && (
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="flex flex-wrap gap-2"
          >
            {QUICK_SUGGESTIONS.map((s) => (
              <button
                key={s.label}
                onClick={() => handleSuggestionClick(s.label)}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 rounded-full border border-border/60
                           bg-background px-3 py-1.5 text-xs text-muted-foreground
                           hover:bg-accent hover:text-accent-foreground hover:border-accent
                           transition-all duration-200 hover:shadow-sm
                           disabled:opacity-50 disabled:pointer-events-none"
              >
                <span>{s.icon}</span>
                <span>{s.label}</span>
              </button>
            ))}
          </motion.div>
        </AnimatePresence>
      )}

      {/* Input Bar */}
      <div
        className={`relative flex items-end gap-2 rounded-2xl border border-border/60
                     bg-background shadow-lg transition-all duration-300
                     focus-within:border-primary/40 focus-within:shadow-xl focus-within:shadow-primary/5
                     ${compact ? "p-2" : "p-3"}`}
      >
        {/* Language Toggle */}
        <div className="flex-shrink-0 flex items-center">
          {showLangPicker ? (
            <div className="flex items-center gap-1">
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger className="h-8 w-[80px] text-xs border-0 bg-muted/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LANGUAGES.map((l) => (
                    <SelectItem key={l.value} value={l.value} className="text-xs">
                      {l.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setShowLangPicker(false)}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
              onClick={() => setShowLangPicker(true)}
              title="Change language"
            >
              <Globe className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Textarea */}
        <TextareaAutosize
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          maxRows={compact ? 3 : 6}
          minRows={1}
          className="flex-1 resize-none bg-transparent text-sm leading-relaxed
                     placeholder:text-muted-foreground/60 focus:outline-none
                     disabled:opacity-50 py-1.5"
        />

        {/* Action Buttons */}
        <div className="flex-shrink-0 flex items-center gap-1">
          {/* Voice Toggle */}
          {!compact && (
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 w-8 p-0 transition-colors ${
                isListening
                  ? "text-destructive animate-pulse"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={toggleVoice}
              title={isListening ? "Stop recording" : "Voice input"}
            >
              {isListening ? (
                <MicOff className="h-4 w-4" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </Button>
          )}

          {/* Send Button */}
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            size="sm"
            className={`${
              compact ? "h-8 w-8 p-0" : "h-9 px-3"
            } rounded-xl bg-gradient-to-r from-primary to-chart-1 text-primary-foreground
              shadow-md hover:shadow-lg transition-all duration-200
              disabled:opacity-40 disabled:shadow-none`}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Send className="h-4 w-4" />
                {!compact && <span className="ml-1.5 text-xs">Send</span>}
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Local Mode Notice */}
      {!compact && (
        <div className="flex items-center justify-center gap-1.5 text-[10px] text-muted-foreground/50">
          <Sparkles className="h-3 w-3" />
          <span>Powered by local NVIDIA NIM — Llama 3.1 70B · All data stays on your machine</span>
        </div>
      )}
    </div>
  );
}
