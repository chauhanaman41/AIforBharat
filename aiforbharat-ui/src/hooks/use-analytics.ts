"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { useAppStore } from "@/lib/store";

/**
 * AIforBharat — Analytics, Dashboard & Trust Hooks (Phase 5)
 * =============================================================
 * Hooks for:
 *  - Dashboard BFF (E14) → /dashboard/*
 *  - Analytics Warehouse (E13) → /analytics/*
 *  - Trust Scoring (E19) → /trust/*
 *  - Engine Health (E0 Orchestrator) → /engines/health
 *
 * All calls → http://localhost:8000/api/v1
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface DashboardWidgetData {
  widget: string;
  title: string;
  data_url: string;
  refresh_seconds: number;
  icon: string;
  languages?: string[];
}

export interface DashboardHomeData {
  user_id: string;
  widgets: DashboardWidgetData[];
  navigation: Array<{ label: string; path: string; icon: string }>;
  quick_actions: Array<{ label: string; action: string; icon: string }>;
}

export interface EngineHealthEntry {
  engine: string;
  status: "healthy" | "unreachable";
  port: string;
  uptime?: number;
}

export interface EngineHealthData {
  total: number;
  healthy: number;
  unhealthy: number;
  engines: EngineHealthEntry[];
}

export interface AnalyticsSummary {
  total_events: number;
  unique_users: number;
  uptime_seconds: number;
  top_event_types: Array<{ type: string; count: number }>;
  top_schemes: Array<{ scheme: string; count: number }>;
  top_engines: Array<{ engine: string; count: number }>;
}

export interface AnalyticsEvent {
  id: string;
  event_type: string;
  user_id?: string;
  engine?: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface TrustScoreData {
  overall_score: number;
  trust_level: string;
  components: Record<string, { score: number; weight: number; details: string[] }>;
  positive_factors: string[];
  negative_factors: string[];
  computed_at?: string;
}

export interface TrustHistoryEntry {
  score: number;
  level: string;
  computed_at: string;
}

export interface SchemePopularity {
  scheme: string;
  interactions: number;
}

// ── Dashboard BFF (E14) ─────────────────────────────────────────────────────

export function useDashboardHome() {
  const user = useAppStore((s) => s.user);
  return useQuery({
    queryKey: ["dashboard", "home", user?.user_id],
    queryFn: async () => {
      const res = await apiClient.get<{ data: DashboardHomeData }>(
        `/dashboard/home/${user?.user_id}`
      );
      return res.data.data;
    },
    enabled: !!user?.user_id,
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

// ── Engine Health (E0 Orchestrator) ──────────────────────────────────────────

export function useEngineHealth() {
  return useQuery({
    queryKey: ["engines", "health"],
    queryFn: async () => {
      const res = await apiClient.get<{ data: EngineHealthData }>(
        "/engines/health"
      );
      return res.data.data;
    },
    refetchInterval: 30_000, // poll every 30s
    staleTime: 15_000,
  });
}

// ── Analytics Warehouse (E13) ───────────────────────────────────────────────

export function useAnalyticsSummary() {
  return useQuery({
    queryKey: ["analytics", "dashboard"],
    queryFn: async () => {
      const res = await apiClient.get<{ data: AnalyticsSummary }>(
        "/analytics/dashboard"
      );
      return res.data.data;
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

export function useAnalyticsEvents(filters?: {
  event_type?: string;
  engine?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["analytics", "events", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.event_type) params.set("event_type", filters.event_type);
      if (filters?.engine) params.set("engine", filters.engine);
      if (filters?.limit) params.set("limit", String(filters.limit));
      const res = await apiClient.get<{ data: AnalyticsEvent[] }>(
        `/analytics/events/query?${params.toString()}`
      );
      return res.data.data;
    },
    staleTime: 30_000,
  });
}

export function useSchemePopularity() {
  return useQuery({
    queryKey: ["analytics", "scheme-popularity"],
    queryFn: async () => {
      const res = await apiClient.get<{ data: SchemePopularity[] }>(
        "/analytics/scheme-popularity"
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

// ── Trust Scoring (E19) ─────────────────────────────────────────────────────

export function useTrustScore() {
  const user = useAppStore((s) => s.user);
  return useQuery({
    queryKey: ["trust", "score", user?.user_id],
    queryFn: async () => {
      const res = await apiClient.get<{ data: TrustScoreData }>(
        `/trust/user/${user?.user_id}`
      );
      return res.data.data;
    },
    enabled: !!user?.user_id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTrustHistory() {
  const user = useAppStore((s) => s.user);
  return useQuery({
    queryKey: ["trust", "history", user?.user_id],
    queryFn: async () => {
      const res = await apiClient.get<{ data: TrustHistoryEntry[] }>(
        `/trust/user/${user?.user_id}/history`
      );
      return res.data.data;
    },
    enabled: !!user?.user_id,
    staleTime: 60_000,
  });
}

export function useComputeTrust() {
  return useMutation({
    mutationFn: async (data: { profile: Record<string, unknown> }) => {
      const user = useAppStore.getState().user;
      const res = await apiClient.post<{ data: TrustScoreData }>(
        "/trust/compute",
        { user_id: user?.user_id, profile: data.profile }
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      toast.success("Trust score computed", {
        description: `Score: ${data.overall_score}/100 — Level: ${data.trust_level}`,
      });
    },
    onError: (error: Error) => {
      toast.error("Trust computation failed", { description: error.message });
    },
  });
}
