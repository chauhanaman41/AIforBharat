"use client";

/**
 * CRITICAL: import d3-transition BEFORE reactflow so that the side-effect
 * patches `selection.prototype.interrupt` onto d3-selection v3.
 * Without this, d3-zoom (used by ReactFlow zoom/pan and Controls) crashes
 * with "selection.interrupt is not a function".
 */
import "d3-transition";

import { useMemo, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  type Node,
  type Edge,
  Position,
  MarkerType,
  Handle,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";

import { useEngineHealth, type EngineHealthEntry } from "@/hooks/use-analytics";

/**
 * EngineStatusMap — React Flow visualization of the 21-engine architecture.
 *
 * Displays each engine as a node with real-time health status (green/red).
 * Edges show the data flow between engines as defined by the orchestrator.
 * Uses the GET /engines/health orchestrator endpoint for live status.
 */

// ── Engine metadata (name, label, group, position) ──────────────────────────

interface EngineMeta {
  id: string;
  label: string;
  group: "core" | "data" | "ai" | "user" | "system";
  port: number;
  x: number;
  y: number;
}

const ENGINE_META: EngineMeta[] = [
  // Core orchestration
  { id: "api_gateway",         label: "API Gateway (E0)",        group: "core",   port: 8000, x: 400, y: 0   },
  // User engines
  { id: "login_register",      label: "Login/Register (E1)",     group: "user",   port: 8001, x: 100, y: 120 },
  { id: "identity",            label: "Identity (E2)",           group: "user",   port: 8002, x: 280, y: 120 },
  { id: "json_user_info",      label: "User Info (E12)",         group: "user",   port: 8012, x: 100, y: 240 },
  // Data engines
  { id: "raw_data_store",      label: "Raw Data (E3)",           group: "data",   port: 8003, x: 460, y: 120 },
  { id: "metadata",            label: "Metadata (E4)",           group: "data",   port: 8004, x: 640, y: 120 },
  { id: "processed_metadata",  label: "Processed Meta (E5)",     group: "data",   port: 8005, x: 640, y: 240 },
  { id: "vector_database",     label: "Vector DB (E6)",          group: "data",   port: 8006, x: 460, y: 240 },
  // AI engines
  { id: "neural_network",      label: "Neural Net (E7)",         group: "ai",     port: 8007, x: 280, y: 360 },
  { id: "anomaly_detection",   label: "Anomaly Det. (E8)",       group: "ai",     port: 8008, x: 460, y: 360 },
  { id: "chunks",              label: "Chunks (E9)",             group: "ai",     port: 8009, x: 640, y: 360 },
  { id: "speech_interface",    label: "Speech (E20)",            group: "ai",     port: 8020, x: 100, y: 360 },
  { id: "doc_understanding",   label: "Doc Engine (E21)",        group: "ai",     port: 8021, x: 100, y: 480 },
  // System engines
  { id: "policy_fetching",     label: "Policy Fetch (E10)",      group: "system", port: 8010, x: 280, y: 480 },
  { id: "eligibility_rules",   label: "Eligibility (E15)",       group: "system", port: 8015, x: 460, y: 480 },
  { id: "deadline_monitoring",  label: "Deadlines (E16)",        group: "system", port: 8016, x: 640, y: 480 },
  { id: "simulation",          label: "Simulation (E17)",        group: "system", port: 8017, x: 820, y: 360 },
  { id: "gov_data_sync",       label: "Gov Sync (E18)",          group: "system", port: 8018, x: 820, y: 480 },
  { id: "trust_scoring",       label: "Trust Score (E19)",       group: "system", port: 8019, x: 820, y: 240 },
  { id: "analytics_warehouse", label: "Analytics (E13)",         group: "system", port: 8013, x: 820, y: 120 },
  { id: "dashboard_bff",       label: "Dashboard (E14)",         group: "system", port: 8014, x: 820, y: 0   },
];

// ── Edge definitions (orchestrator data flow) ───────────────────────────────

const EDGE_DEFS: Array<{ source: string; target: string; label?: string }> = [
  // Orchestrator → all engines
  { source: "api_gateway", target: "login_register", label: "Auth" },
  { source: "api_gateway", target: "identity", label: "ID" },
  { source: "api_gateway", target: "neural_network", label: "AI" },
  { source: "api_gateway", target: "raw_data_store", label: "Audit" },
  { source: "api_gateway", target: "analytics_warehouse", label: "Events" },
  { source: "api_gateway", target: "eligibility_rules", label: "Rules" },
  { source: "api_gateway", target: "simulation", label: "Sim" },
  { source: "api_gateway", target: "trust_scoring", label: "Trust" },
  { source: "api_gateway", target: "speech_interface", label: "Voice" },
  { source: "api_gateway", target: "dashboard_bff", label: "BFF" },
  // RAG pipeline
  { source: "neural_network", target: "vector_database", label: "Search" },
  { source: "vector_database", target: "neural_network", label: "Context" },
  { source: "neural_network", target: "anomaly_detection", label: "Check" },
  { source: "neural_network", target: "trust_scoring", label: "Score" },
  // Data flow
  { source: "identity", target: "raw_data_store", label: "Store" },
  { source: "metadata", target: "processed_metadata" },
  { source: "processed_metadata", target: "chunks", label: "Chunk" },
  { source: "chunks", target: "vector_database", label: "Embed" },
  { source: "policy_fetching", target: "metadata" },
  { source: "gov_data_sync", target: "policy_fetching" },
  // Eligibility pipeline
  { source: "eligibility_rules", target: "neural_network", label: "Explain" },
  { source: "simulation", target: "eligibility_rules" },
  // Dashboard
  { source: "dashboard_bff", target: "analytics_warehouse" },
];

// ── Group colors ─────────────────────────────────────────────────────────────

const GROUP_COLORS: Record<string, { bg: string; border: string }> = {
  core:   { bg: "bg-blue-500/15",    border: "border-blue-500/40"   },
  user:   { bg: "bg-purple-500/15",  border: "border-purple-500/40" },
  data:   { bg: "bg-amber-500/15",   border: "border-amber-500/40"  },
  ai:     { bg: "bg-green-500/15",   border: "border-green-500/40"  },
  system: { bg: "bg-cyan-500/15",    border: "border-cyan-500/40"   },
};

// ── Custom Node Component ───────────────────────────────────────────────────

interface EngineNodeData {
  label: string;
  group: string;
  port: number;
  status: "healthy" | "unreachable" | "unknown";
  uptime?: number;
}

function EngineNode({ data }: NodeProps<EngineNodeData>) {
  const colors = GROUP_COLORS[data.group] || GROUP_COLORS.system;
  const statusColor =
    data.status === "healthy"
      ? "bg-green-500"
      : data.status === "unreachable"
        ? "bg-red-500"
        : "bg-gray-400";

  return (
    <div
      className={`px-3 py-2 rounded-lg border ${colors.bg} ${colors.border} min-w-[140px] shadow-sm`}
    >
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground !w-2 !h-2" />
      <div className="flex items-center gap-2">
        <div className={`h-2.5 w-2.5 rounded-full ${statusColor} engine-status-pulse`} />
        <span className="text-[11px] font-medium leading-tight">{data.label}</span>
      </div>
      <div className="flex items-center justify-between mt-1">
        <span className="text-[9px] text-muted-foreground">:{data.port}</span>
        {data.uptime !== undefined && (
          <span className="text-[9px] text-muted-foreground">
            {Math.round(data.uptime / 60)}m
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { engine: EngineNode };

// ── Main Component ──────────────────────────────────────────────────────────

interface EngineStatusMapProps {
  className?: string;
}

export default function EngineStatusMap({ className }: EngineStatusMapProps) {
  const { data: healthData } = useEngineHealth();

  // Build status lookup
  const statusMap = useMemo(() => {
    const map: Record<string, EngineHealthEntry> = {};
    if (healthData?.engines) {
      for (const e of healthData.engines) {
        map[e.engine] = e;
      }
    }
    return map;
  }, [healthData]);

  // Convert to React Flow nodes
  const nodes: Node[] = useMemo(
    () =>
      ENGINE_META.map((e) => ({
        id: e.id,
        type: "engine",
        position: { x: e.x, y: e.y },
        data: {
          label: e.label,
          group: e.group,
          port: e.port,
          status: statusMap[e.id]?.status ?? "unknown",
          uptime: statusMap[e.id]?.uptime,
        } as EngineNodeData,
      })),
    [statusMap]
  );

  // Convert to React Flow edges
  const edges: Edge[] = useMemo(
    () =>
      EDGE_DEFS.map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: { stroke: "hsl(var(--muted-foreground))", strokeWidth: 1.2, opacity: 0.5 },
        labelStyle: { fontSize: 9, fill: "hsl(var(--muted-foreground))" },
        markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12 },
      })),
    []
  );

  return (
    <ReactFlowProvider>
      <div className={`w-full h-full min-h-[500px] rounded-lg border border-border overflow-hidden ${className ?? ""}`}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          proOptions={{ hideAttribution: true }}
          minZoom={0.3}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
        >
          <Background gap={20} size={1} className="!bg-background" />
          <Controls className="!bg-card !border-border !shadow-sm" />
          <MiniMap
            nodeColor={(node) => {
              const d = node.data as EngineNodeData;
              if (d.status === "healthy") return "#22c55e";
              if (d.status === "unreachable") return "#ef4444";
              return "#9ca3af";
            }}
            className="!bg-card !border-border"
          />
        </ReactFlow>
      </div>
    </ReactFlowProvider>
  );
}
