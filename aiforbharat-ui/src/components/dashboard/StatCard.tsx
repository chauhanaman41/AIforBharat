"use client";

import { type LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardBody, Progress } from "@nextui-org/react";

/**
 * StatCard — Hero UI (NextUI) metric card with animated progress/value.
 *
 * Used across the dashboard home page and analytics views.
 * Libraries: Hero UI (Card, Progress), Framer Motion, Lucide React
 */

interface StatCardProps {
  title: string;
  description?: string;
  value: string | number;
  icon: LucideIcon;
  color: string;
  progress?: number;         // 0–100 optional progress bar
  trend?: number;            // +/- trend value
  href?: string;
  index?: number;            // for stagger animation
}

export default function StatCard({
  title,
  description,
  value,
  icon: Icon,
  color,
  progress,
  trend,
  index = 0,
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
    >
      <Card isPressable className="border border-border/40 stat-card-lift">
        <CardBody className="p-4">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{title}</p>
              {description && (
                <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                  {description}
                </p>
              )}
            </div>
            <div className={`h-9 w-9 rounded-xl flex items-center justify-center flex-shrink-0 ${color}/10`}>
              <Icon className={`h-4.5 w-4.5 ${color}`} />
            </div>
          </div>

          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold leading-none">{value}</span>
            {trend !== undefined && trend !== 0 && (
              <span
                className={`text-xs font-medium ${
                  trend > 0 ? "text-green-500" : "text-red-500"
                }`}
              >
                {trend > 0 ? "+" : ""}{trend}%
              </span>
            )}
          </div>

          {progress !== undefined && (
            <Progress
              value={progress}
              size="sm"
              color={progress >= 70 ? "success" : progress >= 40 ? "warning" : "danger"}
              className="mt-3"
            />
          )}
        </CardBody>
      </Card>
    </motion.div>
  );
}
