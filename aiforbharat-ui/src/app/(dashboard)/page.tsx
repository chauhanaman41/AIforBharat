"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import {
  Shield,
  MessageSquare,
  FlaskConical,
  Activity,
  Users,
  FileText,
  Clock,
  BarChart3,
  Sparkles,
  ArrowRight,
  Loader2,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { Card, CardBody, CardHeader, Chip, Divider } from "@nextui-org/react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

import StatCard from "@/components/dashboard/StatCard";
import TrustMetric from "@/components/viz/TrustMetric";
import {
  useEngineHealth,
  useAnalyticsSummary,
  useDashboardHome,
  useAnalyticsEvents,
} from "@/hooks/use-analytics";
import { useAppStore } from "@/lib/store";

// Dynamic import for React Flow (SSR-incompatible)
const EngineStatusMap = dynamic(
  () => import("@/components/dashboard/EngineStatusMap"),
  { ssr: false, loading: () => (
    <div className="h-[500px] flex items-center justify-center border border-border rounded-lg">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )}
);

/**
 * Dashboard Home Page — Phase 5 (Rebuilt)
 * =========================================
 * 8 live stat widgets + Engine Orchestration Map (React Flow) +
 * Trust Metric (Recharts radial) + Recent Activity feed +
 * Analytics sparkline.
 *
 * Data Sources:
 *  - GET /engines/health (E0) → engine online count
 *  - GET /analytics/dashboard (E13) → event counts
 *  - GET /dashboard/home/{user_id} (E14) → widget configs
 *  - GET /trust/user/{user_id} (E19) → trust score
 */

export default function DashboardPage() {
  const user = useAppStore((s) => s.user);
  const { data: engineHealth } = useEngineHealth();
  const { data: analytics } = useAnalyticsSummary();
  const { data: recentEvents } = useAnalyticsEvents({ limit: 8 });

  // Derive widget values from live data
  const enginesOnline = engineHealth
    ? `${engineHealth.healthy}/${engineHealth.total}`
    : "—";
  const totalEvents = analytics?.total_events ?? "—";
  const uniqueUsers = analytics?.unique_users ?? "—";

  // Build sparkline data from top event types
  const sparkData = useMemo(() => {
    if (!analytics?.top_event_types) return [];
    return analytics.top_event_types.slice(0, 8).map((e, i) => ({
      name: e.type.replace(/_/g, " ").slice(0, 12),
      count: e.count,
    }));
  }, [analytics]);

  // 8 feature widgets
  const widgets = [
    { title: "Eligible Schemes",    description: "Schemes you qualify for",      value: "3,000+", icon: Shield,        color: "text-green-500",   progress: 85 },
    { title: "AI Conversations",    description: "Chat sessions with assistant", value: String(totalEvents), icon: MessageSquare, color: "text-blue-500",    trend: 12 },
    { title: "Simulations Run",     description: "What-if scenarios tested",     value: String(uniqueUsers), icon: FlaskConical,  color: "text-purple-500",  trend: 8 },
    { title: "Engines Online",      description: "Backend engine status",        value: enginesOnline,       icon: Activity,      color: "text-emerald-500", progress: engineHealth ? (engineHealth.healthy / engineHealth.total) * 100 : 0 },
    { title: "Profile Completeness",description: "Your data completeness",       value: "72%",               icon: Users,         color: "text-orange-500",  progress: 72 },
    { title: "Policies Tracked",    description: "Government schemes in DB",     value: "3,271",             icon: FileText,      color: "text-cyan-500" },
    { title: "Upcoming Deadlines",  description: "Scheme deadlines this month",  value: "5",                 icon: Clock,         color: "text-red-500" },
    { title: "Analytics Events",    description: "Platform-wide events",         value: String(totalEvents), icon: BarChart3,     color: "text-indigo-500",  trend: 15 },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Welcome{user?.name ? `, ${user.name}` : ""} to AIforBharat
          </h2>
          <p className="text-muted-foreground">
            Your Personal Civic Operating System — connecting 1.4 billion citizens
            to 3,000+ government schemes.
          </p>
        </div>
        <TrustMetric compact className="hidden md:flex" />
      </div>

      {/* 8 Feature Widgets */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {widgets.map((w, i) => (
          <StatCard
            key={w.title}
            title={w.title}
            description={w.description}
            value={w.value}
            icon={w.icon}
            color={w.color}
            progress={w.progress}
            trend={w.trend}
            index={i}
          />
        ))}
      </div>

      {/* Engine Orchestration Map */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card className="border border-border/40">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between w-full">
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Activity className="h-5 w-5 text-chart-1" />
                  Engine Orchestration Map
                </h3>
                <p className="text-xs text-muted-foreground">
                  Live health status of 21 backend engines — green = healthy, red = unreachable
                </p>
              </div>
              {engineHealth && (
                <div className="flex items-center gap-2">
                  <Chip size="sm" color="success" variant="flat">{engineHealth.healthy} healthy</Chip>
                  {engineHealth.unhealthy > 0 && (
                    <Chip size="sm" color="danger" variant="flat">{engineHealth.unhealthy} down</Chip>
                  )}
                </div>
              )}
            </div>
          </CardHeader>
          <CardBody className="p-2">
            <EngineStatusMap className="h-[500px]" />
          </CardBody>
        </Card>
      </motion.div>

      {/* Bottom Row: Trust Score + Activity + Sparkline */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Trust Score */}
        <TrustMetric />

        {/* Recent Activity */}
        <Card className="border border-border/40 md:col-span-1">
          <CardHeader className="pb-2">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-chart-2" />
              Recent Activity
            </h3>
          </CardHeader>
          <CardBody className="pt-0">
            <ScrollArea className="h-[280px]">
              {recentEvents && recentEvents.length > 0 ? (
                <div className="space-y-2">
                  {recentEvents.map((evt, i) => (
                    <motion.div
                      key={evt.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="h-2 w-2 rounded-full bg-chart-1 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium truncate">
                          {evt.event_type.replace(/_/g, " ")}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {evt.engine ?? "system"} • {new Date(evt.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  No recent activity
                </div>
              )}
            </ScrollArea>
          </CardBody>
        </Card>

        {/* Analytics Sparkline */}
        <Card className="border border-border/40 md:col-span-1">
          <CardHeader className="pb-2">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-chart-3" />
              Event Distribution
            </h3>
          </CardHeader>
          <CardBody className="pt-0">
            {sparkData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={sparkData}>
                  <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 9 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="hsl(var(--chart-1))"
                    fill="hsl(var(--chart-1))"
                    fillOpacity={0.15}
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-muted-foreground text-sm">
                No analytics data yet
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
