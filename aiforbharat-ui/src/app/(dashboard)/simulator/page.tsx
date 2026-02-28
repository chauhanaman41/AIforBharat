"use client";

import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sliders,
  ArrowRight,
  Loader2,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  Play,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Info,
  GitCompareArrows,
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
  Cell,
} from "recharts";

import { Card, CardBody, CardHeader, Chip, Divider } from "@nextui-org/react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";

import { useSimulation } from "@/hooks/use-eligibility";
import { useAppStore } from "@/lib/store";

/**
 * Simulator Page — Phase 4
 * ===========================
 * "What-If" scenario engine: change profile parameters and see how schemes
 * gained/lost respond in real-time.
 *
 * Libraries: ShadCN (Input, Select, Table), Hero UI (Card, Chip, Divider),
 *            Recharts (BarChart — before/after comparison), Framer Motion
 * Engines: E0 Orchestrator → E17 Simulation → E7 Neural Network (AI explanation)
 */

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
  "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
  "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Delhi", "Jammu and Kashmir",
  "Ladakh", "Lakshadweep", "Puducherry",
];

const CATEGORIES = ["General", "OBC", "SC", "ST", "EWS", "Minority"];
const OCCUPATIONS = ["Farmer", "Student", "Self-Employed", "Salaried", "Unemployed", "Retired", "Homemaker"];
const GENDERS = ["Male", "Female", "Other"];

// ── Helpers ──────────────────────────────────────────────────────────────────

function ImpactBadge({ value }: { value: number }) {
  if (value > 0) {
    return (
      <div className="flex items-center gap-1 text-green-600">
        <TrendingUp className="h-3.5 w-3.5" />
        <span className="text-xs font-semibold">+{value}</span>
      </div>
    );
  }
  if (value < 0) {
    return (
      <div className="flex items-center gap-1 text-red-600">
        <TrendingDown className="h-3.5 w-3.5" />
        <span className="text-xs font-semibold">{value}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1 text-muted-foreground">
      <Minus className="h-3.5 w-3.5" />
      <span className="text-xs font-semibold">0</span>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function SimulatorPage() {
  const user = useAppStore((s) => s.user);
  const simulation = useSimulation();

  // Current profile fields
  const [currentAge, setCurrentAge] = useState("");
  const [currentIncome, setCurrentIncome] = useState("");
  const [currentState, setCurrentState] = useState(user?.state || "");
  const [currentGender, setCurrentGender] = useState("");
  const [currentCategory, setCurrentCategory] = useState("");
  const [currentOccupation, setCurrentOccupation] = useState("");

  // Changes (what-if fields)
  const [newAge, setNewAge] = useState("");
  const [newIncome, setNewIncome] = useState("");
  const [newState, setNewState] = useState("");
  const [newGender, setNewGender] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newOccupation, setNewOccupation] = useState("");

  const [showDetails, setShowDetails] = useState(false);

  const buildProfile = useCallback((): Record<string, unknown> => {
    const p: Record<string, unknown> = {};
    if (currentAge) p.age = parseInt(currentAge);
    if (currentIncome) p.income = parseInt(currentIncome);
    if (currentState) p.state = currentState;
    if (currentGender) p.gender = currentGender.toLowerCase();
    if (currentCategory) p.category = currentCategory.toLowerCase();
    if (currentOccupation) p.occupation = currentOccupation.toLowerCase();
    return p;
  }, [currentAge, currentIncome, currentState, currentGender, currentCategory, currentOccupation]);

  const buildChanges = useCallback((): Record<string, unknown> => {
    const c: Record<string, unknown> = {};
    if (newAge) c.age = parseInt(newAge);
    if (newIncome) c.income = parseInt(newIncome);
    if (newState) c.state = newState;
    if (newGender) c.gender = newGender.toLowerCase();
    if (newCategory) c.category = newCategory.toLowerCase();
    if (newOccupation) c.occupation = newOccupation.toLowerCase();
    return c;
  }, [newAge, newIncome, newState, newGender, newCategory, newOccupation]);

  const handleSimulate = useCallback(() => {
    simulation.mutate({
      current_profile: buildProfile(),
      changes: buildChanges(),
      explain: true,
    });
  }, [simulation, buildProfile, buildChanges]);

  const handleReset = () => {
    setCurrentAge(""); setCurrentIncome(""); setCurrentState(user?.state || "");
    setCurrentGender(""); setCurrentCategory(""); setCurrentOccupation("");
    setNewAge(""); setNewIncome(""); setNewState("");
    setNewGender(""); setNewCategory(""); setNewOccupation("");
  };

  // Chart data
  const chartData = useMemo(() => {
    const d = simulation.data;
    if (!d) return [];
    return [
      { name: "Before", eligible: d.before, fill: "hsl(var(--chart-2))" },
      { name: "After", eligible: d.after, fill: "hsl(var(--chart-1))" },
    ];
  }, [simulation.data]);

  const schemesGained = simulation.data?.schemes_gained ?? [] as Array<{ scheme_id: string; scheme_name: string; category?: string }>;
  const schemesLost = simulation.data?.schemes_lost ?? [] as Array<{ scheme_id: string; scheme_name: string; category?: string }>;
  const delta = simulation.data?.delta ?? 0;
  const netImpact = simulation.data?.net_impact ?? "neutral";

  // ── Profile Field Component ────────────────────────────────────────────

  const ProfileField = ({
    label, type, value, onChange, options, placeholder,
  }: {
    label: string;
    type: "number" | "select";
    value: string;
    onChange: (v: string) => void;
    options?: string[];
    placeholder: string;
  }) => (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {type === "number" ? (
        <Input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="h-9 text-sm"
          min={0}
        />
      ) : (
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger className="h-9 text-sm">
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent>
            {options?.map((o) => (
              <SelectItem key={o} value={o}>{o}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <GitCompareArrows className="h-6 w-6 text-chart-2" />
          What-If Simulator
        </h2>
        <p className="text-muted-foreground">
          Simulate changes to your profile and see which government schemes you gain or lose instantly.
        </p>
      </div>

      {/* Two-Column Layout: Current vs. Changes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Current Profile */}
        <div className="uiverse-glow">
          <Card className="border-0 h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-chart-2" />
                <h3 className="text-base font-semibold">Current Profile</h3>
              </div>
              <p className="text-xs text-muted-foreground">Your existing demographic data</p>
            </CardHeader>
            <CardBody className="space-y-3">
              <ProfileField label="Age" type="number" value={currentAge} onChange={setCurrentAge} placeholder="e.g. 35" />
              <ProfileField label="Annual Income (₹)" type="number" value={currentIncome} onChange={setCurrentIncome} placeholder="e.g. 300000" />
              <ProfileField label="State" type="select" value={currentState} onChange={setCurrentState} options={INDIAN_STATES} placeholder="Select state" />
              <ProfileField label="Gender" type="select" value={currentGender} onChange={setCurrentGender} options={GENDERS} placeholder="Select gender" />
              <ProfileField label="Category" type="select" value={currentCategory} onChange={setCurrentCategory} options={CATEGORIES} placeholder="Select category" />
              <ProfileField label="Occupation" type="select" value={currentOccupation} onChange={setCurrentOccupation} options={OCCUPATIONS} placeholder="Select occupation" />
            </CardBody>
          </Card>
        </div>

        {/* Arrow between columns — Desktop only */}
        <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 pointer-events-none" style={{ display: "none" }}>
          <ArrowRight className="h-8 w-8 text-muted-foreground/30" />
        </div>

        {/* Column 2: What-If Changes */}
        <div className="uiverse-glow">
          <Card className="border-0 h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-chart-1" />
                <h3 className="text-base font-semibold">What-If Changes</h3>
              </div>
              <p className="text-xs text-muted-foreground">Hypothetical modifications to evaluate</p>
            </CardHeader>
            <CardBody className="space-y-3">
              <ProfileField label="New Age" type="number" value={newAge} onChange={setNewAge} placeholder="e.g. 60" />
              <ProfileField label="New Income (₹)" type="number" value={newIncome} onChange={setNewIncome} placeholder="e.g. 150000" />
              <ProfileField label="New State" type="select" value={newState} onChange={setNewState} options={INDIAN_STATES} placeholder="Keep current" />
              <ProfileField label="New Gender" type="select" value={newGender} onChange={setNewGender} options={GENDERS} placeholder="Keep current" />
              <ProfileField label="New Category" type="select" value={newCategory} onChange={setNewCategory} options={CATEGORIES} placeholder="Keep current" />
              <ProfileField label="New Occupation" type="select" value={newOccupation} onChange={setNewOccupation} options={OCCUPATIONS} placeholder="Keep current" />
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3">
        <Button
          onClick={handleSimulate}
          disabled={simulation.isPending}
          className="css-btn-primary"
          size="lg"
        >
          {simulation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Play className="h-4 w-4 mr-2" />
          )}
          {simulation.isPending ? "Simulating..." : "Run Simulation"}
        </Button>
        <Button variant="ghost" onClick={handleReset} className="css-btn-ghost">
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset All
        </Button>
      </div>

      {/* ── Results ────────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {simulation.data && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-6"
          >
            {/* Impact Summary Row */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <Card className="border border-chart-2/20 bg-chart-2/5">
                <CardBody className="p-4 text-center">
                  <p className="text-2xl font-bold">{simulation.data.before}</p>
                  <p className="text-xs text-muted-foreground">Before</p>
                </CardBody>
              </Card>
              <Card className="border border-chart-1/20 bg-chart-1/5">
                <CardBody className="p-4 text-center">
                  <p className="text-2xl font-bold">{simulation.data.after}</p>
                  <p className="text-xs text-muted-foreground">After</p>
                </CardBody>
              </Card>
              <Card className={`border ${delta > 0 ? "border-green-500/20 bg-green-500/5" : delta < 0 ? "border-red-500/20 bg-red-500/5" : "border-border"}`}>
                <CardBody className="p-4 flex flex-col items-center justify-center">
                  <ImpactBadge value={delta} />
                  <p className="text-xs text-muted-foreground mt-1">Delta</p>
                </CardBody>
              </Card>
              <Card className="border border-border">
                <CardBody className="p-4 flex flex-col items-center justify-center">
                  <Chip
                    size="sm"
                    variant="flat"
                    color={netImpact === "positive" ? "success" : netImpact === "negative" ? "danger" : "default"}
                    className="capitalize"
                  >
                    {netImpact}
                  </Chip>
                  <p className="text-xs text-muted-foreground mt-1">Net Impact</p>
                </CardBody>
              </Card>
            </div>

            {/* Recharts — Before vs After */}
            <Card>
              <CardHeader className="pb-0">
                <h3 className="text-base font-semibold">Eligible Schemes Comparison</h3>
              </CardHeader>
              <CardBody className="pt-2">
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={chartData} barGap={20}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="name" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px" }} />
                    <Bar dataKey="eligible" name="Eligible Schemes" radius={[6, 6, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardBody>
            </Card>

            {/* AI Explanation */}
            {simulation.data.explanation && (
              <Card className="border border-chart-1/20 bg-chart-1/5">
                <CardBody className="p-4">
                  <div className="flex items-start gap-3">
                    <Sparkles className="h-5 w-5 text-chart-1 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-chart-1 mb-1">AI Analysis</p>
                      <p className="text-sm leading-relaxed">{simulation.data.explanation}</p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            )}

            {/* Schemes Gained / Lost Tables */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Gained */}
              <Card className="border border-green-500/20">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-green-500" />
                    <h3 className="text-sm font-semibold">Schemes Gained ({schemesGained.length})</h3>
                  </div>
                </CardHeader>
                <CardBody className="pt-0">
                  {schemesGained.length > 0 ? (
                    <ScrollArea className="max-h-[300px]">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-xs">Scheme</TableHead>
                            <TableHead className="text-xs text-right">Confidence</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {schemesGained.map((s, i) => (
                            <TableRow key={i}>
                              <TableCell className="text-sm">{s.scheme_name}</TableCell>
                              <TableCell className="text-right">
                                <Chip size="sm" color="success" variant="flat">New</Chip>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  ) : (
                    <p className="text-xs text-muted-foreground py-4 text-center">No new schemes gained</p>
                  )}
                </CardBody>
              </Card>

              {/* Lost */}
              <Card className="border border-red-500/20">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4 text-red-500" />
                    <h3 className="text-sm font-semibold">Schemes Lost ({schemesLost.length})</h3>
                  </div>
                </CardHeader>
                <CardBody className="pt-0">
                  {schemesLost.length > 0 ? (
                    <ScrollArea className="max-h-[300px]">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-xs">Scheme</TableHead>
                            <TableHead className="text-xs text-right">Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {schemesLost.map((s, i) => (
                            <TableRow key={i}>
                              <TableCell className="text-sm">{s.scheme_name}</TableCell>
                              <TableCell className="text-right">
                                <Chip size="sm" color="danger" variant="flat">Lost</Chip>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  ) : (
                    <p className="text-xs text-muted-foreground py-4 text-center">No schemes lost</p>
                  )}
                </CardBody>
              </Card>
            </div>

            {/* Degraded Engines Warning */}
            {simulation.data.degraded && simulation.data.degraded.length > 0 && (
              <Card className="border border-amber-500/20 bg-amber-500/5">
                <CardBody className="p-3">
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-amber-500" />
                    <p className="text-xs text-amber-700">
                      Some engines responded in degraded mode: {simulation.data.degraded.join(", ")}
                    </p>
                  </div>
                </CardBody>
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty State */}
      {!simulation.data && !simulation.isPending && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="h-16 w-16 rounded-3xl bg-chart-2/10 flex items-center justify-center mb-4">
            <Sliders className="h-8 w-8 text-chart-2" />
          </div>
          <h3 className="text-lg font-semibold mb-1">Ready to Simulate</h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Enter your current profile on the left, specify hypothetical changes on the right,
            and click &quot;Run Simulation&quot; to see how your eligibility would change.
          </p>
        </div>
      )}
    </div>
  );
}
