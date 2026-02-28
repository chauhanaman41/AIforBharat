"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import {
  BarChart3,
  TrendingUp,
  Layers,
  Globe,
  Cpu,
  Loader2,
  RefreshCw,
  Filter,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from "recharts";

import { Card, CardBody, CardHeader, Chip, Divider } from "@nextui-org/react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";

import StatCard from "@/components/dashboard/StatCard";
import TrustMetric from "@/components/viz/TrustMetric";
import {
  useAnalyticsSummary,
  useAnalyticsEvents,
  useSchemePopularity,
  useEngineHealth,
} from "@/hooks/use-analytics";

// Dynamic imports (SSR-incompatible)
const DistrictMap = dynamic(
  () => import("@/components/viz/DistrictMap"),
  { ssr: false, loading: () => (
    <div className="h-[450px] flex items-center justify-center border border-border rounded-lg">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )}
);
const EngineStatusMap = dynamic(
  () => import("@/components/dashboard/EngineStatusMap"),
  { ssr: false, loading: () => (
    <div className="h-[500px] flex items-center justify-center border border-border rounded-lg">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )}
);

/**
 * Analytics Page — Phase 5
 * ==========================
 * Comprehensive analytics dashboard with 4 tabs:
 *  1. Overview — Summary stats + event distribution + scheme popularity
 *  2. Geospatial — India district map (react-simple-maps)
 *  3. Engines — React Flow orchestration map + engine health table
 *  4. Trust — Full trust score breakdown
 *
 * Data Sources:
 *  - GET /analytics/dashboard (E13)
 *  - GET /analytics/events/query (E13)
 *  - GET /analytics/scheme-popularity (E13)
 *  - GET /engines/health (E0)
 *  - GET /trust/user/{user_id} (E19)
 */

const PIE_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "#f59e0b",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
  "#10b981",
];

export default function AnalyticsPage() {
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();
  const { data: events } = useAnalyticsEvents({ limit: 20 });
  const { data: schemePopularity } = useSchemePopularity();
  const { data: engineHealth } = useEngineHealth();

  const [engineFilter, setEngineFilter] = useState<string>("all");

  // Prepare chart data
  const eventTypeData = useMemo(() => {
    if (!summary?.top_event_types) return [];
    return summary.top_event_types.map((e) => ({
      name: e.type.replace(/_/g, " ").slice(0, 18),
      count: e.count,
    }));
  }, [summary]);

  const engineCallData = useMemo(() => {
    if (!summary?.top_engines) return [];
    return summary.top_engines.map((e) => ({
      name: e.engine.replace(/_/g, " ").slice(0, 14),
      calls: e.count,
    }));
  }, [summary]);

  const schemeData = useMemo(() => {
    if (!schemePopularity) return [];
    return schemePopularity.slice(0, 10).map((s) => ({
      name: s.scheme.slice(0, 20),
      interactions: s.interactions,
    }));
  }, [schemePopularity]);

  // Engine health table data
  const filteredEngines = useMemo(() => {
    if (!engineHealth?.engines) return [];
    if (engineFilter === "all") return engineHealth.engines;
    return engineHealth.engines.filter((e) => e.status === engineFilter);
  }, [engineHealth, engineFilter]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-chart-1" />
          Analytics Dashboard
        </h2>
        <p className="text-muted-foreground">
          Platform-wide analytics, geospatial insights, engine health monitoring, and trust metrics.
        </p>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full max-w-lg grid-cols-4">
          <TabsTrigger value="overview">
            <TrendingUp className="h-4 w-4 mr-1.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="geospatial">
            <Globe className="h-4 w-4 mr-1.5" />
            Map
          </TabsTrigger>
          <TabsTrigger value="engines">
            <Cpu className="h-4 w-4 mr-1.5" />
            Engines
          </TabsTrigger>
          <TabsTrigger value="trust">
            <Layers className="h-4 w-4 mr-1.5" />
            Trust
          </TabsTrigger>
        </TabsList>

        {/* ── TAB 1: Overview ────────────────────────────────────────────── */}
        <TabsContent value="overview" className="space-y-6">
          {/* Summary Stat Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Total Events"
              value={summary?.total_events ?? "—"}
              icon={BarChart3}
              color="text-blue-500"
              index={0}
            />
            <StatCard
              title="Unique Users"
              value={summary?.unique_users ?? "—"}
              icon={TrendingUp}
              color="text-green-500"
              index={1}
            />
            <StatCard
              title="Engines Online"
              value={engineHealth ? `${engineHealth.healthy}/${engineHealth.total}` : "—"}
              icon={Cpu}
              color="text-emerald-500"
              progress={engineHealth ? (engineHealth.healthy / engineHealth.total) * 100 : 0}
              index={2}
            />
            <StatCard
              title="Uptime"
              value={summary ? `${Math.round(summary.uptime_seconds / 3600)}h` : "—"}
              icon={RefreshCw}
              color="text-purple-500"
              index={3}
            />
          </div>

          {/* Charts Row */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Event Type Distribution */}
            <Card className="border border-border/40">
              <CardHeader className="pb-2">
                <h3 className="text-sm font-semibold">Event Distribution</h3>
              </CardHeader>
              <CardBody className="pt-0">
                {eventTypeData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={eventTypeData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
                      <YAxis tick={{ fontSize: 9 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                      />
                      <Bar dataKey="count" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
                    No event data yet
                  </div>
                )}
              </CardBody>
            </Card>

            {/* Engine Call Distribution (Pie) */}
            <Card className="border border-border/40">
              <CardHeader className="pb-2">
                <h3 className="text-sm font-semibold">Engine Call Share</h3>
              </CardHeader>
              <CardBody className="pt-0">
                {engineCallData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={engineCallData}
                        dataKey="calls"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        innerRadius={50}
                        paddingAngle={2}
                        label={(props) => `${String(props.name ?? "")} ${(((props.percent as number) ?? 0) * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {engineCallData.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
                    No engine call data
                  </div>
                )}
              </CardBody>
            </Card>
          </div>

          {/* Scheme Popularity */}
          <Card className="border border-border/40">
            <CardHeader className="pb-2">
              <h3 className="text-sm font-semibold">Top Schemes by Interactions</h3>
            </CardHeader>
            <CardBody className="pt-0">
              {schemeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={schemeData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-15} textAnchor="end" height={50} />
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
                      dataKey="interactions"
                      stroke="hsl(var(--chart-2))"
                      fill="hsl(var(--chart-2))"
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[250px] text-muted-foreground text-sm">
                  No scheme popularity data
                </div>
              )}
            </CardBody>
          </Card>

          {/* Recent Events Table */}
          <Card className="border border-border/40">
            <CardHeader className="pb-2">
              <h3 className="text-sm font-semibold">Recent Events</h3>
            </CardHeader>
            <CardBody className="pt-0 p-0">
              <ScrollArea className="max-h-[300px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Event Type</TableHead>
                      <TableHead className="text-xs">Engine</TableHead>
                      <TableHead className="text-xs hidden md:table-cell">User</TableHead>
                      <TableHead className="text-xs text-right">Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {events?.map((evt) => (
                      <TableRow key={evt.id}>
                        <TableCell className="text-sm">
                          <Chip size="sm" variant="flat" color="primary">
                            {evt.event_type.replace(/_/g, " ")}
                          </Chip>
                        </TableCell>
                        <TableCell className="text-xs">{evt.engine ?? "—"}</TableCell>
                        <TableCell className="text-xs hidden md:table-cell">{evt.user_id ?? "—"}</TableCell>
                        <TableCell className="text-xs text-right">
                          {new Date(evt.created_at).toLocaleTimeString()}
                        </TableCell>
                      </TableRow>
                    )) ?? (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                          No events recorded
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardBody>
          </Card>
        </TabsContent>

        {/* ── TAB 2: Geospatial ──────────────────────────────────────────── */}
        <TabsContent value="geospatial" className="space-y-4">
          <DistrictMap />
        </TabsContent>

        {/* ── TAB 3: Engines ─────────────────────────────────────────────── */}
        <TabsContent value="engines" className="space-y-6">
          {/* Engine Flow Map */}
          <Card className="border border-border/40">
            <CardHeader className="pb-2">
              <h3 className="text-sm font-semibold">Engine Data Flow</h3>
              <p className="text-[10px] text-muted-foreground">
                React Flow visualization of the 21-engine orchestration architecture
              </p>
            </CardHeader>
            <CardBody className="p-2">
              <EngineStatusMap className="h-[500px]" />
            </CardBody>
          </Card>

          {/* Engine Health Table */}
          <Card className="border border-border/40">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <h3 className="text-sm font-semibold">Engine Health Status</h3>
              <Select value={engineFilter} onValueChange={setEngineFilter}>
                <SelectTrigger className="w-[140px] h-8 text-xs">
                  <Filter className="h-3 w-3 mr-1" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Engines</SelectItem>
                  <SelectItem value="healthy">Healthy</SelectItem>
                  <SelectItem value="unreachable">Unreachable</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            <CardBody className="pt-0 p-0">
              <ScrollArea className="max-h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Engine</TableHead>
                      <TableHead className="text-xs">Port</TableHead>
                      <TableHead className="text-xs">Status</TableHead>
                      <TableHead className="text-xs text-right">Uptime</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredEngines.map((eng) => (
                      <TableRow key={eng.engine}>
                        <TableCell className="text-sm font-medium">
                          {eng.engine.replace(/_/g, " ")}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          :{eng.port}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div
                              className={`h-2 w-2 rounded-full ${
                                eng.status === "healthy"
                                  ? "bg-green-500 engine-status-pulse"
                                  : "bg-red-500"
                              }`}
                            />
                            <Chip
                              size="sm"
                              variant="flat"
                              color={eng.status === "healthy" ? "success" : "danger"}
                              className="capitalize text-[10px]"
                            >
                              {eng.status}
                            </Chip>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs text-right">
                          {eng.uptime ? `${Math.round(eng.uptime / 60)}m` : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardBody>
          </Card>
        </TabsContent>

        {/* ── TAB 4: Trust ───────────────────────────────────────────────── */}
        <TabsContent value="trust" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            <TrustMetric />
            <Card className="border border-border/40">
              <CardHeader className="pb-2">
                <h3 className="text-sm font-semibold">About Trust Scoring</h3>
              </CardHeader>
              <CardBody className="pt-0 space-y-3">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Your Trust Score (0–100) is computed by Engine E19 using 5 weighted
                  dimensions: data completeness, anomaly detection, behavioral consistency,
                  source reliability, and identity verification.
                </p>
                <Divider />
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span>Data Completeness</span>
                    <Chip size="sm" variant="flat">25% weight</Chip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Anomaly Check</span>
                    <Chip size="sm" variant="flat">20% weight</Chip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Consistency</span>
                    <Chip size="sm" variant="flat">20% weight</Chip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Behavior</span>
                    <Chip size="sm" variant="flat">15% weight</Chip>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Verification</span>
                    <Chip size="sm" variant="flat">20% weight</Chip>
                  </div>
                </div>
                <Divider />
                <p className="text-[10px] text-muted-foreground">
                  Trust scores are refreshed every 5 minutes and stored locally in the
                  Trust Scoring Engine (port 8019). No external verification services.
                </p>
              </CardBody>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
