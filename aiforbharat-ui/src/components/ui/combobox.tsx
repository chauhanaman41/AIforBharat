"use client";

import * as React from "react";
import { CheckIcon, ChevronDownIcon, Search } from "lucide-react";
import { Popover as PopoverPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────────────────────
 * Combobox
 * ─────────────────────────────────────────────────────────────────────────────
 * A searchable dropdown built on Radix Popover + native filtering.
 * Matches the ShadCN design language (border, bg‑popover, focus ring, etc.)
 * and supports full keyboard navigation (Arrow keys, Enter, Escape).
 *
 * Usage:
 *   <Combobox
 *     items={[{ value: "gj", label: "Gujarat" }]}
 *     value={selected}
 *     onValueChange={setSelected}
 *     placeholder="Select state"
 *     searchPlaceholder="Search states…"
 *   />
 * ───────────────────────────────────────────────────────────────────────────*/

export interface ComboboxItem {
  value: string;
  label: string;
}

interface ComboboxProps {
  items: ComboboxItem[];
  value?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  className?: string;
  disabled?: boolean;
  emptyMessage?: string;
}

export function Combobox({
  items,
  value,
  onValueChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  className,
  disabled = false,
  emptyMessage = "No results found.",
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listRef = React.useRef<HTMLDivElement>(null);
  const [highlightedIndex, setHighlightedIndex] = React.useState(0);

  // Filter items by search string
  const filtered = React.useMemo(() => {
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter((item) => item.label.toLowerCase().includes(q));
  }, [items, search]);

  // Reset highlight when filtered list changes
  React.useEffect(() => {
    setHighlightedIndex(0);
  }, [filtered.length]);

  // Auto-focus search input when popover opens
  React.useEffect(() => {
    if (open) {
      // Small delay for Radix portal mount
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    } else {
      setSearch("");
    }
  }, [open]);

  // Scroll highlighted item into view
  React.useEffect(() => {
    if (!open || !listRef.current) return;
    const highlighted = listRef.current.querySelector(
      `[data-index="${highlightedIndex}"]`
    );
    highlighted?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex, open]);

  const selectedLabel = items.find((i) => i.value === value)?.label;

  function handleSelect(itemValue: string) {
    onValueChange?.(itemValue === value ? "" : itemValue);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((p) => Math.min(p + 1, filtered.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((p) => Math.max(p - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (filtered[highlightedIndex]) {
          handleSelect(filtered[highlightedIndex].value);
        }
        break;
      case "Escape":
        setOpen(false);
        break;
    }
  }

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild disabled={disabled}>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          className={cn(
            "border-input data-[placeholder]:text-muted-foreground [&_svg:not([class*='text-'])]:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 dark:bg-input/30 dark:hover:bg-input/50 flex w-full items-center justify-between gap-2 rounded-md border bg-transparent px-3 py-2 text-sm whitespace-nowrap shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
        >
          <span
            className={cn(
              "truncate",
              !selectedLabel && "text-muted-foreground"
            )}
          >
            {selectedLabel ?? placeholder}
          </span>
          <ChevronDownIcon className="size-4 opacity-50 shrink-0" />
        </button>
      </PopoverPrimitive.Trigger>

      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="bottom"
          align="start"
          sideOffset={4}
          className={cn(
            "bg-popover text-popover-foreground z-50 w-[var(--radix-popover-trigger-width)] min-w-[200px] max-h-[300px] overflow-hidden rounded-md border shadow-md",
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2"
          )}
          onKeyDown={handleKeyDown}
        >
          {/* Search input */}
          <div className="flex items-center border-b px-3 py-2">
            <Search className="mr-2 size-4 shrink-0 opacity-50" />
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>

          {/* Items list */}
          <div
            ref={listRef}
            role="listbox"
            className="overflow-y-auto max-h-[220px] p-1"
          >
            {filtered.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                {emptyMessage}
              </div>
            ) : (
              filtered.map((item, index) => (
                <div
                  key={item.value}
                  role="option"
                  aria-selected={value === item.value}
                  data-index={index}
                  onClick={() => handleSelect(item.value)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={cn(
                    "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none transition-colors",
                    index === highlightedIndex && "bg-accent text-accent-foreground",
                    value === item.value && "font-medium"
                  )}
                >
                  <CheckIcon
                    className={cn(
                      "size-4 shrink-0",
                      value === item.value ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <span className="truncate">{item.label}</span>
                </div>
              ))
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
