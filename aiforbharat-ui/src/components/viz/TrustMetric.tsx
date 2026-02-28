"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PolarAngleAxis,
} from "recharts";
import { Shield, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";

import { Card, CardBody, Chip, Divider, Progress } from "@nextui-org/react";
import { useTrustScore, useTrustHistory, type TrustScoreData } from "@/hooks/use-analytics";

/**
 * TrustMetric — Trust Score visualization component.
 *
 * Shows:
 *  - Radial gauge for overall trust score (0–100)
 *  - Component breakdown bars (data_completeness, anomaly, consistency, behavior, verification)
 *  - Positive/negative factor pills
 *  - Trust level badge
 *
 * Data: GET /trust/user/{user_id} (E19)
 * Libraries: Recharts (RadialBarChart), Hero UI (Card, Chip, Progress), Framer Motion
 */

const LEVEL_COLORS: Record<string, { color: string; chip: "success" | "warning" | "danger" | "default" }> = {
  high:     { color: "#22c55e", chip: "success" },
  medium:   { color: "#f59e0b", chip: "warning" },
  low:      { color: "#ef4444", chip: "danger"  },
  unknown:  { color: "#9ca3af", chip: "default" },
};

const COMPONENT_LABELS: Record<string, string> = {
  data_completeness: "Data Completeness",
  anomaly_check:     "Anomaly Check",
  consistency:       "Consistency",
  behavior:          "Behavior",
  verification:      "Verification",
};

interface TrustMetricProps {
  className?: string;
  compact?: boolean;
}

export default function TrustMetric({ className, compact }: TrustMetricProps) {
  const { data: trust, isLoading } = useTrustScore();
  const { data: history } = useTrustHistory();

  const score = trust?.overall_score ?? 0;
  const level = trust?.trust_level ?? "unknown";
  const levelInfo = LEVEL_COLORS[level] ?? LEVEL_COLORS.unknown;

  const gaugeData = useMemo(() => [{ name: "Trust", value: score, fill: levelInfo.color }], [score, levelInfo]);

  // Trend from history (last 2 entries)
  const trend = useMemo(() => {
    if (!history || history.length < 2) return 0;
    return history[0].score - history[1].score;
  }, [history]);

  if (isLoading) {
    return (
      <Card className={`${className ?? ""}`}>
        <CardBody className="flex items-center justify-center py-12">
          <div className="h-8 w-8 border-2 border-chart-1 border-t-transparent rounded-full animate-spin" />
        </CardBody>
      </Card>
    );
  }

  if (compact) {
    return (
      <div className={`flex items-center gap-3 ${className ?? ""}`}>
        <div className="relative h-14 w-14">
          <ResponsiveContainer>
            <RadialBarChart
              innerRadius="70%"
              outerRadius="100%"
              data={gaugeData}
              startAngle={90}
              endAngle={-270}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
              <RadialBar dataKey="value" cornerRadius={10} background={{ fill: "hsl(var(--muted))" }} />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs font-bold">{score}</span>
          </div>
        </div>
        <div>
          <p className="text-sm font-medium">Trust Score</p>
          <Chip size="sm" color={levelInfo.chip} variant="flat" className="capitalize text-[10px]">
            {level}
          </Chip>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={className}
    >
      <Card className="border border-border/40">
        <CardBody className="space-y-4 p-5">
          {/* Header Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" style={{ color: levelInfo.color }} />
              <h3 className="text-base font-semibold">Trust Score</h3>
            </div>
            <div className="flex items-center gap-2">
              {trend !== 0 && (
                <div className={`flex items-center gap-1 text-xs ${trend > 0 ? "text-green-500" : "text-red-500"}`}>
                  {trend > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {trend > 0 ? "+" : ""}{trend.toFixed(1)}
                </div>
              )}
              <Chip size="sm" color={levelInfo.chip} variant="flat" className="capitalize">
                {level}
              </Chip>
            </div>
          </div>

          {/* Radial Gauge */}
          <div className="flex justify-center">
            <div className="relative h-36 w-36">
              <ResponsiveContainer>
                <RadialBarChart
                  innerRadius="65%"
                  outerRadius="100%"
                  data={gaugeData}
                  startAngle={90}
                  endAngle={-270}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="value" cornerRadius={10} background={{ fill: "hsl(var(--muted))" }} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold">{score}</span>
                <span className="text-[10px] text-muted-foreground">/100</span>
              </div>
            </div>
          </div>

          <Divider />

          {/* Component Breakdown */}
          {trust?.components && (
            <div className="space-y-2.5">
              <p className="text-xs font-medium text-muted-foreground">Component Breakdown</p>
              {Object.entries(trust.components).map(([key, comp]) => (
                <div key={key} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs">{COMPONENT_LABELS[key] || key}</span>
                    <span className="text-xs text-muted-foreground">
                      {Math.round(comp.score)}/100
                    </span>
                  </div>
                  <Progress
                    value={comp.score}
                    size="sm"
                    color={comp.score >= 70 ? "success" : comp.score >= 40 ? "warning" : "danger"}
                    className="max-w-full"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Factors */}
          {(trust?.positive_factors?.length || trust?.negative_factors?.length) && (
            <>
              <Divider />
              <div className="space-y-2">
                {trust?.positive_factors && trust.positive_factors.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-green-600 mb-1">Positive Factors</p>
                    <div className="flex flex-wrap gap-1">
                      {trust.positive_factors.map((f, i) => (
                        <span key={i} className="source-pill text-green-700">
                          <TrendingUp className="h-2.5 w-2.5" />
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {trust?.negative_factors && trust.negative_factors.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-red-600 mb-1">Risk Factors</p>
                    <div className="flex flex-wrap gap-1">
                      {trust.negative_factors.map((f, i) => (
                        <span key={i} className="source-pill text-red-700">
                          <AlertTriangle className="h-2.5 w-2.5" />
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </CardBody>
      </Card>
    </motion.div>
  );
}
