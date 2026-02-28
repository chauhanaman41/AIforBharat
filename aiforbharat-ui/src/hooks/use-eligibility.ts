"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
import type {
  EligibilityCheckRequest,
  EligibilityCheckResponse,
  EligibilityResult,
  SimulateRequest,
  SimulateResponse,
} from "@/types/api";

/**
 * AIforBharat — Eligibility & Simulation Hooks (Phase 4)
 * ========================================================
 * Hooks for the Eligibility Rules Engine (E15) and Simulation Engine (E17),
 * both routed through the Orchestrator (E0) for AI explanations.
 *
 * Endpoints:
 *  - POST /check-eligibility  → Orchestrator composite (E15→E7→Audit)
 *  - GET  /eligibility/history/{user_id} → E15 direct
 *  - POST /simulate           → Orchestrator composite (E17→E7→Audit)
 *
 * All calls → http://localhost:8000/api/v1
 * No AWS, no external services.
 */

// ── Extended Types for Orchestrator Responses ───────────────────────────────

export interface EligibilityOrchResponse extends EligibilityCheckResponse {
  explanation?: string;
  degraded?: string[] | null;
}

export interface SimulateOrchResponse {
  before: number;
  after: number;
  delta: number;
  schemes_gained: Array<{ scheme_id: string; scheme_name: string; category?: string }>;
  schemes_lost: Array<{ scheme_id: string; scheme_name: string; category?: string }>;
  net_impact: "positive" | "negative" | "neutral";
  explanation?: string;
  degraded?: string[] | null;
}

// ── Eligibility Check (E0 → E15 → E7) ──────────────────────────────────────

export function useEligibilityCheck() {
  return useMutation({
    mutationFn: async (data: {
      profile: Record<string, unknown>;
      scheme_ids?: string[];
      explain?: boolean;
    }) => {
      const user = useAppStore.getState().user;
      const res = await apiClient.post<{ data: EligibilityOrchResponse }>(
        "/check-eligibility",
        {
          user_id: user?.user_id || "anonymous",
          profile: data.profile,
          scheme_ids: data.scheme_ids,
          explain: data.explain ?? true,
        }
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      const eligible = data.results?.filter(
        (r: EligibilityResult) => r.verdict === "eligible"
      ).length ?? 0;
      toast.success(`Eligibility check complete`, {
        description: `You're eligible for ${eligible} out of ${data.total_schemes_checked} schemes checked.`,
      });
    },
    onError: (error: Error) => {
      toast.error("Eligibility check failed", { description: error.message });
    },
  });
}

// ── Eligibility History (E15 direct) ────────────────────────────────────────

export function useEligibilityHistory() {
  const user = useAppStore((s) => s.user);

  return useQuery({
    queryKey: ["eligibility-history", user?.user_id],
    queryFn: async () => {
      const res = await apiClient.get<{ data: EligibilityResult[] }>(
        `/eligibility/history/${user?.user_id}`
      );
      return res.data.data;
    },
    enabled: !!user?.user_id,
    staleTime: 60_000,
  });
}

// ── What-If Simulation (E0 → E17 → E7) ─────────────────────────────────────

export function useSimulation() {
  return useMutation({
    mutationFn: async (data: {
      current_profile: Record<string, unknown>;
      changes: Record<string, unknown>;
      explain?: boolean;
    }) => {
      const user = useAppStore.getState().user;
      const res = await apiClient.post<{ data: SimulateOrchResponse }>(
        "/simulate",
        {
          user_id: user?.user_id || "anonymous",
          current_profile: data.current_profile,
          changes: data.changes,
          explain: data.explain ?? true,
        }
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      const gained = data.schemes_gained?.length ?? 0;
      const lost = data.schemes_lost?.length ?? 0;
      toast.success("Simulation complete", {
        description: `${gained} schemes gained, ${lost} schemes lost. Net impact: ${data.net_impact}`,
      });
    },
    onError: (error: Error) => {
      toast.error("Simulation failed", { description: error.message });
    },
  });
}
