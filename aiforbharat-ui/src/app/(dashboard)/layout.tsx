"use client";

import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/shared/Sidebar";
import { Navbar } from "@/components/shared/Navbar";
import { ChatWidget } from "@/components/chat/ChatWidget";

/**
 * Dashboard Layout — Wraps all authenticated pages with:
 *  - ShadCN SidebarProvider (collapsible sidebar with cookie persistence)
 *  - AppSidebar (main navigation)
 *  - Navbar (top bar with search, theme toggle, notifications)
 *  - Main content area with proper insets
 *  - ChatWidget (floating AI assistant — Phase 3)
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <Navbar />
        <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
      </SidebarInset>
      <ChatWidget />
    </SidebarProvider>
  );
}
