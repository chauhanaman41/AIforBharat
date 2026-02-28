"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Shield,
  MessageSquare,
  User,
  FlaskConical,
  Activity,
  BarChart3,
  LogOut,
  ChevronLeft,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";

import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { useLogout } from "@/hooks/use-auth";

// ── Navigation Items ─────────────────────────────────────────────────────────

interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
}

const mainNav: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    title: "Eligibility",
    href: "/eligibility",
    icon: Shield,
  },
  {
    title: "Simulator",
    href: "/simulator",
    icon: FlaskConical,
  },
  {
    title: "AI Chat",
    href: "/chat",
    icon: MessageSquare,
  },
  {
    title: "Profile",
    href: "/profile",
    icon: User,
  },
];

const systemNav: NavItem[] = [
  {
    title: "Engine Status",
    href: "/engines",
    icon: Activity,
  },
];

// ── Sidebar Component ────────────────────────────────────────────────────────

export function AppSidebar() {
  const pathname = usePathname();
  const { state, toggleSidebar } = useSidebar();
  const logoutMutation = useLogout();
  const user = useAppStore((s) => s.user);
  const isCollapsed = state === "collapsed";

  return (
    <ShadcnSidebar collapsible="icon" className="border-r border-sidebar-border">
      {/* Header / Brand */}
      <SidebarHeader className="px-3 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm shrink-0">
            AI
          </div>
          {!isCollapsed && (
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold">AIforBharat</span>
              <span className="text-xs text-muted-foreground">
                Civic OS
              </span>
            </div>
          )}
        </div>
      </SidebarHeader>

      <Separator />

      {/* Main Navigation */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNav.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={item.title}
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="mx-3" />

        {/* System */}
        <SidebarGroup>
          <SidebarGroupLabel>System</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {systemNav.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={item.title}
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Footer */}
      <SidebarFooter className="px-3 py-3">
        <Separator className="mb-3" />
        {/* User info */}
        {user && !isCollapsed && (
          <div className="mb-2 px-2">
            <p className="text-xs font-medium truncate">{user.name}</p>
            <p className="text-xs text-muted-foreground truncate">
              {user.phone}
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={toggleSidebar}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
      </SidebarFooter>

      <SidebarRail />
    </ShadcnSidebar>
  );
}
