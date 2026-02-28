"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Languages,
  FileText,
  Brain,
  ChevronDown,
  ChevronUp,
  Loader2,
  Copy,
  Check,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAiTranslate, useAiSummarize, useAiIntent } from "@/hooks/use-chat";

/**
 * NlpToolbar — Quick NLP Action Tools
 * ======================================
 * CUI Kit / Prompt Kit inspired toolbar providing direct access to
 * individual NLP engines without going through the chat flow:
 *  - Translate (POST /ai/translate)
 *  - Summarize (POST /ai/summarize)
 *  - Classify Intent (POST /ai/intent)
 *
 * Libraries: ShadCN Card/Input/Select/Button, Framer Motion, Lucide
 */

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी (Hindi)" },
  { value: "bn", label: "বাংলা (Bengali)" },
  { value: "te", label: "తెలుగు (Telugu)" },
  { value: "mr", label: "मराठी (Marathi)" },
  { value: "ta", label: "தமிழ் (Tamil)" },
  { value: "gu", label: "ગુજરાતી (Gujarati)" },
  { value: "kn", label: "ಕನ್ನಡ (Kannada)" },
  { value: "ml", label: "മലയാളം (Malayalam)" },
  { value: "pa", label: "ਪੰਜਾਬੀ (Punjabi)" },
  { value: "or", label: "ଓଡ଼ିଆ (Odia)" },
  { value: "as", label: "অসমীয়া (Assamese)" },
];

// ── Translate Tool ──────────────────────────────────────────────────────────

function TranslateTool() {
  const [text, setText] = useState("");
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("hi");
  const [copied, setCopied] = useState(false);
  const translateMutation = useAiTranslate();

  const handleTranslate = () => {
    if (!text.trim()) return;
    translateMutation.mutate({
      text,
      source_lang: sourceLang,
      target_lang: targetLang,
    });
  };

  const handleCopy = async () => {
    if (translateMutation.data?.translated) {
      await navigator.clipboard.writeText(translateMutation.data.translated);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Select value={sourceLang} onValueChange={setSourceLang}>
          <SelectTrigger className="w-[130px] h-8 text-xs">
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
        <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <Select value={targetLang} onValueChange={setTargetLang}>
          <SelectTrigger className="w-[130px] h-8 text-xs">
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
      </div>
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter text to translate..."
        className="text-sm"
      />
      <Button
        onClick={handleTranslate}
        disabled={!text.trim() || translateMutation.isPending}
        size="sm"
        className="w-full css-btn-primary"
      >
        {translateMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <Languages className="h-4 w-4 mr-2" />
        )}
        Translate
      </Button>
      {translateMutation.data && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative rounded-lg bg-muted/60 p-3 text-sm"
        >
          <p className="pr-8">{translateMutation.data.translated}</p>
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 h-6 w-6 p-0"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
        </motion.div>
      )}
    </div>
  );
}

// ── Summarize Tool ──────────────────────────────────────────────────────────

function SummarizeTool() {
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);
  const summarizeMutation = useAiSummarize();

  const handleSummarize = () => {
    if (!text.trim()) return;
    summarizeMutation.mutate({ text, max_length: 150 });
  };

  const handleCopy = async () => {
    if (summarizeMutation.data?.summary) {
      await navigator.clipboard.writeText(summarizeMutation.data.summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste scheme text or policy document to summarize..."
        rows={3}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm
                   placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring
                   resize-none"
      />
      <Button
        onClick={handleSummarize}
        disabled={!text.trim() || summarizeMutation.isPending}
        size="sm"
        className="w-full css-btn-primary"
      >
        {summarizeMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <FileText className="h-4 w-4 mr-2" />
        )}
        Summarize
      </Button>
      {summarizeMutation.data && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative rounded-lg bg-muted/60 p-3 text-sm space-y-1"
        >
          <p className="pr-8">{summarizeMutation.data.summary}</p>
          <p className="text-[10px] text-muted-foreground">
            Compressed from {summarizeMutation.data.original_length} characters
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 h-6 w-6 p-0"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
        </motion.div>
      )}
    </div>
  );
}

// ── Intent Classifier Tool ──────────────────────────────────────────────────

function IntentTool() {
  const [text, setText] = useState("");
  const intentMutation = useAiIntent();

  const handleClassify = () => {
    if (!text.trim()) return;
    intentMutation.mutate({ message: text });
  };

  return (
    <div className="space-y-3">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type a message to classify intent..."
        className="text-sm"
      />
      <Button
        onClick={handleClassify}
        disabled={!text.trim() || intentMutation.isPending}
        size="sm"
        className="w-full css-btn-primary"
      >
        {intentMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <Brain className="h-4 w-4 mr-2" />
        )}
        Classify Intent
      </Button>
      {intentMutation.data && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg bg-muted/60 p-3 text-sm space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium capitalize">{intentMutation.data.intent}</span>
            <span className="text-xs text-muted-foreground">
              {Math.round(intentMutation.data.confidence * 100)}% confidence
            </span>
          </div>
          {intentMutation.data.language && (
            <p className="text-xs text-muted-foreground">
              Language: {intentMutation.data.language}
            </p>
          )}
          {intentMutation.data.entities && Object.keys(intentMutation.data.entities).length > 0 && (
            <div className="text-xs space-y-1">
              <p className="font-medium text-muted-foreground">Entities:</p>
              {Object.entries(intentMutation.data.entities).map(([key, val]) => (
                <div key={key} className="flex gap-2">
                  <span className="text-muted-foreground capitalize">{key}:</span>
                  <span>{val}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}

// ── Main NlpToolbar Component ───────────────────────────────────────────────

interface NlpToolbarProps {
  defaultExpanded?: boolean;
}

export function NlpToolbar({ defaultExpanded = false }: NlpToolbarProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [activeTool, setActiveTool] = useState<"translate" | "summarize" | "intent" | null>(null);

  const tools = [
    { id: "translate" as const, label: "Translate", icon: Languages, description: "Between Indian languages" },
    { id: "summarize" as const, label: "Summarize", icon: FileText, description: "Simplify scheme text" },
    { id: "intent" as const, label: "Classify", icon: Brain, description: "Detect query intent" },
  ];

  return (
    <Card className="border-border/40">
      <CardHeader className="py-3 px-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Brain className="h-4 w-4 text-chart-1" />
            NLP Tools
          </CardTitle>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CardHeader>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <CardContent className="pt-0 px-4 pb-4 space-y-3">
              {/* Tool Selector */}
              <div className="grid grid-cols-3 gap-2">
                {tools.map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => setActiveTool(activeTool === tool.id ? null : tool.id)}
                    className={`flex flex-col items-center gap-1 rounded-xl p-2.5 text-xs
                               transition-all duration-200 border
                               ${
                                 activeTool === tool.id
                                   ? "border-primary bg-primary/5 text-primary shadow-sm"
                                   : "border-border/40 hover:border-border hover:bg-muted/50 text-muted-foreground"
                               }`}
                  >
                    <tool.icon className="h-4 w-4" />
                    <span className="font-medium">{tool.label}</span>
                  </button>
                ))}
              </div>

              <Separator />

              {/* Tool Content */}
              <AnimatePresence mode="wait">
                {activeTool === "translate" && (
                  <motion.div
                    key="translate"
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                  >
                    <TranslateTool />
                  </motion.div>
                )}
                {activeTool === "summarize" && (
                  <motion.div
                    key="summarize"
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                  >
                    <SummarizeTool />
                  </motion.div>
                )}
                {activeTool === "intent" && (
                  <motion.div
                    key="intent"
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                  >
                    <IntentTool />
                  </motion.div>
                )}
              </AnimatePresence>

              {!activeTool && (
                <p className="text-center text-xs text-muted-foreground py-4">
                  Select a tool above to use NLP features directly
                </p>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
