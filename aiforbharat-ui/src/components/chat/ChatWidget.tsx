"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Maximize2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AssistantOverlay } from "./AssistantOverlay";

/**
 * ChatWidget — Floating AI Chat Bubble
 * =======================================
 * CopilotKit / assistant-ui inspired floating widget available on
 * all dashboard pages. Features:
 *  - Floating action button (bottom-right)
 *  - Expandable chat panel with smooth animation
 *  - Compact AssistantOverlay inside the panel
 *  - Full-page link to /chat for expanded view
 *  - Keyboard shortcut: Ctrl+K to toggle
 *
 * Libraries: Framer Motion (AnimatePresence), ShadCN Button
 */

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [hasNewMessage, setHasNewMessage] = useState(false);

  // Keyboard shortcut: Ctrl+K to toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen]);

  // Simulate new message indicator after 3s on first mount
  useEffect(() => {
    const t = setTimeout(() => setHasNewMessage(true), 3000);
    return () => clearTimeout(t);
  }, []);

  const handleToggle = () => {
    setIsOpen(!isOpen);
    setHasNewMessage(false);
  };

  return (
    <>
      {/* Floating Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop (mobile only) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden"
              onClick={() => setIsOpen(false)}
            />

            {/* Chat Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="fixed bottom-20 right-4 z-50 w-[380px] h-[540px]
                         rounded-2xl border border-border/60 bg-background
                         shadow-2xl overflow-hidden flex flex-col
                         max-md:bottom-0 max-md:right-0 max-md:left-0
                         max-md:w-full max-md:h-[85vh] max-md:rounded-b-none max-md:rounded-t-2xl"
            >
              {/* Widget Header */}
              <div className="flex items-center justify-between px-4 py-2.5
                              bg-gradient-to-r from-primary/5 to-chart-1/5 border-b border-border/30">
                <span className="text-xs font-medium text-muted-foreground">
                  AI Assistant
                  <kbd className="ml-2 hidden sm:inline-flex items-center gap-0.5
                                  rounded border bg-muted px-1.5 py-0.5 text-[9px]
                                  font-mono text-muted-foreground">
                    Ctrl+K
                  </kbd>
                </span>
                <div className="flex items-center gap-1">
                  <Link href="/chat">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                      title="Open full chat"
                    >
                      <Maximize2 className="h-3.5 w-3.5" />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                    onClick={() => setIsOpen(false)}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Chat Content */}
              <AssistantOverlay compact showHeader={false} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Floating Action Button */}
      <motion.button
        onClick={handleToggle}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="fixed bottom-4 right-4 z-50 flex h-14 w-14 items-center justify-center
                   rounded-2xl bg-gradient-to-br from-primary to-chart-1
                   text-primary-foreground shadow-xl
                   hover:shadow-2xl hover:shadow-primary/20
                   transition-shadow duration-300"
        title="AI Assistant (Ctrl+K)"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <X className="h-6 w-6" />
            </motion.div>
          ) : (
            <motion.div
              key="open"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <MessageCircle className="h-6 w-6" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* New message indicator */}
        {hasNewMessage && !isOpen && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive
                       flex items-center justify-center"
          >
            <span className="text-[8px] font-bold text-destructive-foreground">1</span>
          </motion.div>
        )}
      </motion.button>
    </>
  );
}
