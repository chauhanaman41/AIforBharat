"use client";

import { usePathname } from "next/navigation";
import { Bell, Search, Sun, Moon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useAppStore } from "@/lib/store";

/**
 * Navbar — Top navigation bar for the dashboard.
 * Features:
 *  - ShadCN SidebarTrigger for mobile toggle
 *  - Breadcrumb-style page title from current route
 *  - Global search input (placeholder for Phase 5)
 *  - Theme toggle (light/dark)
 *  - Notification bell (local only — no external push)
 */

const routeTitles: Record<string, string> = {
  "/": "Dashboard",
  "/eligibility": "Eligibility Check",
  "/simulator": "What-If Simulator",
  "/chat": "AI Assistant",
  "/profile": "My Profile",
  "/engines": "Engine Status",
  "/login": "Login",
};

export function Navbar() {
  const pathname = usePathname();
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);

  const pageTitle = routeTitles[pathname] ?? "AIforBharat";

  const toggleTheme = () => {
    if (theme === "dark") {
      setTheme("light");
      document.documentElement.classList.remove("dark");
    } else {
      setTheme("dark");
      document.documentElement.classList.add("dark");
    }
  };

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-4 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
      {/* Mobile sidebar trigger */}
      <SidebarTrigger className="md:hidden" />

      <Separator orientation="vertical" className="h-6 hidden md:block" />

      {/* Page Title */}
      <h1 className="text-lg font-semibold tracking-tight">{pageTitle}</h1>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search (placeholder — fullly implemented in Phase 5) */}
      <div className="hidden md:flex items-center">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search schemes..."
            className="w-64 pl-8 h-9"
            aria-label="Search schemes"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>

        {/* Notifications (local only — no external push services) */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 relative"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          {/* Badge dot for unread — static for Phase 1 */}
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
        </Button>
      </div>
    </header>
  );
}
