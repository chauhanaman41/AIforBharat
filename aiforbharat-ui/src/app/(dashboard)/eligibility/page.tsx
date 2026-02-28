"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Search,
  Loader2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Filter,
  RotateCcw,
  Info,
  FileText,
  ShieldCheck,
} from "lucide-react";

import { Card, CardBody, CardHeader, Chip, Progress, Divider } from "@nextui-org/react";

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

import { useEligibilityCheck, useEligibilityHistory } from "@/hooks/use-eligibility";
import type { EligibilityResult } from "@/types/api";
import { useAppStore } from "@/lib/store";

/**
 * Eligibility Page — Phase 4
 * ============================
 * Two tabs:
 *   1. Check Eligibility — Profile form → POST /check-eligibility (Orchestrator)
 *   2. History — Previous results → GET /eligibility/history/{user_id}
 *
 * Libraries: ShadCN (Table, Tabs, Select, Input), Hero UI (Card, Chip, Progress, Divider),
 *            UIverse (.uiverse-glow card), Framer Motion (AnimatePresence)
 * Engines: E0 Orchestrator → E15 Eligibility Rules → E7 Neural Network (AI explanation)
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

// ── Verdict Display Helpers ─────────────────────────────────────────────────

function VerdictIcon({ verdict }: { verdict: string }) {
  switch (verdict) {
    case "eligible":
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case "ineligible":
      return <XCircle className="h-5 w-5 text-red-500" />;
    case "partial":
      return <AlertTriangle className="h-5 w-5 text-amber-500" />;
    default:
      return <Info className="h-5 w-5 text-muted-foreground" />;
  }
}

function verdictColor(verdict: string): "success" | "danger" | "warning" | "default" {
  switch (verdict) {
    case "eligible": return "success";
    case "ineligible": return "danger";
    case "partial": return "warning";
    default: return "default";
  }
}

// ── Result Row (Expandable) ─────────────────────────────────────────────────

function ResultRow({ result, index }: { result: EligibilityResult; index: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card
        isPressable
        onPress={() => setExpanded(!expanded)}
        className="mb-2 border border-border/40"
      >
        <CardBody className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <VerdictIcon verdict={result.verdict} />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-sm truncate">{result.scheme_name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {result.scheme_id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Chip size="sm" color={verdictColor(result.verdict)} variant="flat" className="capitalize">
                {result.verdict}
              </Chip>
              <span className="text-xs text-muted-foreground hidden sm:inline">
                {Math.round(result.confidence * 100)}%
              </span>
              {expanded ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </div>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <Divider className="my-3" />
                <div className="space-y-3">
                  {/* Explanation */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Explanation</p>
                    <p className="text-sm leading-relaxed">{result.explanation}</p>
                  </div>

                  {/* Matched Rules */}
                  {result.matched_rules && result.matched_rules.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Matched Rules</p>
                      <div className="flex flex-wrap gap-1.5">
                        {result.matched_rules.map((rule, i) => (
                          <span key={i} className="source-pill">
                            <CheckCircle className="h-2.5 w-2.5 text-green-500" />
                            {rule}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Missing Criteria */}
                  {result.missing_criteria && result.missing_criteria.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Missing Criteria</p>
                      <div className="flex flex-wrap gap-1.5">
                        {result.missing_criteria.map((c, i) => (
                          <span key={i} className="source-pill">
                            <XCircle className="h-2.5 w-2.5 text-red-400" />
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Confidence Bar */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">
                      Confidence: {Math.round(result.confidence * 100)}%
                    </p>
                    <Progress
                      value={result.confidence * 100}
                      color={verdictColor(result.verdict)}
                      size="sm"
                      className="max-w-xs"
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardBody>
      </Card>
    </motion.div>
  );
}

// ── Main Page Component ─────────────────────────────────────────────────────

export default function EligibilityPage() {
  const user = useAppStore((s) => s.user);
  const eligibilityCheck = useEligibilityCheck();
  const { data: history, isLoading: historyLoading } = useEligibilityHistory();

  // Profile form state
  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [state, setState] = useState(user?.state || "");
  const [gender, setGender] = useState("");
  const [category, setCategory] = useState("");
  const [occupation, setOccupation] = useState("");
  const [filterVerdict, setFilterVerdict] = useState<string>("all");

  const handleCheck = useCallback(() => {
    const profile: Record<string, unknown> = {};
    if (age) profile.age = parseInt(age);
    if (income) profile.income = parseInt(income);
    if (state) profile.state = state;
    if (gender) profile.gender = gender.toLowerCase();
    if (category) profile.category = category.toLowerCase();
    if (occupation) profile.occupation = occupation.toLowerCase();

    eligibilityCheck.mutate({ profile, explain: true });
  }, [age, income, state, gender, category, occupation, eligibilityCheck]);

  const handleReset = () => {
    setAge("");
    setIncome("");
    setState(user?.state || "");
    setGender("");
    setCategory("");
    setOccupation("");
  };

  // Filter results
  const results = eligibilityCheck.data?.results ?? [];
  const filtered = filterVerdict === "all"
    ? results
    : results.filter((r) => r.verdict === filterVerdict);

  const eligibleCount = results.filter((r) => r.verdict === "eligible").length;
  const partialCount = results.filter((r) => r.verdict === "partial").length;
  const ineligibleCount = results.filter((r) => r.verdict === "ineligible").length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-chart-1" />
          Eligibility Check
        </h2>
        <p className="text-muted-foreground">
          Check your eligibility across 3,000+ government schemes using deterministic rules with AI-powered explanations.
        </p>
      </div>

      <Tabs defaultValue="check" className="space-y-4">
        <TabsList className="grid w-full max-w-sm grid-cols-2">
          <TabsTrigger value="check">
            <Search className="h-4 w-4 mr-1.5" />
            Check Now
          </TabsTrigger>
          <TabsTrigger value="history">
            <FileText className="h-4 w-4 mr-1.5" />
            History
          </TabsTrigger>
        </TabsList>

        {/* ── TAB 1: Check Eligibility ─────────────────────────────────────── */}
        <TabsContent value="check" className="space-y-6">
          {/* Profile Input Form */}
          <div className="uiverse-glow">
            <Card className="border-0">
              <CardHeader className="pb-2">
                <h3 className="text-lg font-semibold">Your Profile</h3>
                <p className="text-xs text-muted-foreground">
                  Enter your details for accurate eligibility matching. All fields are optional — more data means better results.
                </p>
              </CardHeader>
              <CardBody className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {/* Age */}
                  <div className="space-y-2">
                    <Label htmlFor="age" className="text-xs">Age</Label>
                    <Input
                      id="age"
                      type="number"
                      placeholder="e.g. 35"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      min={0}
                      max={120}
                    />
                  </div>

                  {/* Annual Income */}
                  <div className="space-y-2">
                    <Label htmlFor="income" className="text-xs">Annual Income (₹)</Label>
                    <Input
                      id="income"
                      type="number"
                      placeholder="e.g. 300000"
                      value={income}
                      onChange={(e) => setIncome(e.target.value)}
                      min={0}
                    />
                  </div>

                  {/* State */}
                  <div className="space-y-2">
                    <Label className="text-xs">State</Label>
                    <Select value={state} onValueChange={setState}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select state" />
                      </SelectTrigger>
                      <SelectContent>
                        {INDIAN_STATES.map((s) => (
                          <SelectItem key={s} value={s}>{s}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Gender */}
                  <div className="space-y-2">
                    <Label className="text-xs">Gender</Label>
                    <Select value={gender} onValueChange={setGender}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select gender" />
                      </SelectTrigger>
                      <SelectContent>
                        {GENDERS.map((g) => (
                          <SelectItem key={g} value={g}>{g}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Category */}
                  <div className="space-y-2">
                    <Label className="text-xs">Category</Label>
                    <Select value={category} onValueChange={setCategory}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        {CATEGORIES.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Occupation */}
                  <div className="space-y-2">
                    <Label className="text-xs">Occupation</Label>
                    <Select value={occupation} onValueChange={setOccupation}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select occupation" />
                      </SelectTrigger>
                      <SelectContent>
                        {OCCUPATIONS.map((o) => (
                          <SelectItem key={o} value={o}>{o}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Separator />

                <div className="flex items-center gap-3">
                  <Button
                    onClick={handleCheck}
                    disabled={eligibilityCheck.isPending}
                    className="css-btn-primary"
                  >
                    {eligibilityCheck.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Search className="h-4 w-4 mr-2" />
                    )}
                    {eligibilityCheck.isPending ? "Checking..." : "Check Eligibility"}
                  </Button>
                  <Button variant="ghost" onClick={handleReset} className="css-btn-ghost">
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Reset
                  </Button>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Results Section */}
          {eligibilityCheck.data && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              {/* Summary Stats */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="border border-green-500/20 bg-green-500/5">
                  <CardBody className="p-4 flex flex-row items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-green-500/10 flex items-center justify-center">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-green-600">{eligibleCount}</p>
                      <p className="text-xs text-muted-foreground">Eligible</p>
                    </div>
                  </CardBody>
                </Card>
                <Card className="border border-amber-500/20 bg-amber-500/5">
                  <CardBody className="p-4 flex flex-row items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                      <AlertTriangle className="h-5 w-5 text-amber-500" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-amber-600">{partialCount}</p>
                      <p className="text-xs text-muted-foreground">Partial Match</p>
                    </div>
                  </CardBody>
                </Card>
                <Card className="border border-red-500/20 bg-red-500/5">
                  <CardBody className="p-4 flex flex-row items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                      <XCircle className="h-5 w-5 text-red-500" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-red-600">{ineligibleCount}</p>
                      <p className="text-xs text-muted-foreground">Ineligible</p>
                    </div>
                  </CardBody>
                </Card>
              </div>

              {/* AI Explanation */}
              {eligibilityCheck.data.explanation && (
                <Card className="border border-chart-1/20 bg-chart-1/5">
                  <CardBody className="p-4">
                    <div className="flex items-start gap-3">
                      <Sparkles className="h-5 w-5 text-chart-1 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-medium text-chart-1 mb-1">AI Summary</p>
                        <p className="text-sm leading-relaxed">{eligibilityCheck.data.explanation}</p>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Filter + Results List */}
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">
                  Results ({results.length} schemes)
                </h3>
                <Select value={filterVerdict} onValueChange={setFilterVerdict}>
                  <SelectTrigger className="w-[150px] h-8 text-xs">
                    <Filter className="h-3 w-3 mr-1" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Verdicts</SelectItem>
                    <SelectItem value="eligible">Eligible</SelectItem>
                    <SelectItem value="partial">Partial</SelectItem>
                    <SelectItem value="ineligible">Ineligible</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <ScrollArea className="max-h-[600px]">
                {filtered.length > 0 ? (
                  filtered.map((result, i) => (
                    <ResultRow key={result.scheme_id} result={result} index={i} />
                  ))
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <p>No schemes match the selected filter.</p>
                  </div>
                )}
              </ScrollArea>
            </motion.div>
          )}

          {/* Empty State */}
          {!eligibilityCheck.data && !eligibilityCheck.isPending && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="h-16 w-16 rounded-3xl bg-chart-1/10 flex items-center justify-center mb-4">
                <ShieldCheck className="h-8 w-8 text-chart-1" />
              </div>
              <h3 className="text-lg font-semibold mb-1">Ready to Check</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Fill in your profile details above and click &quot;Check Eligibility&quot; to see
                which government schemes you qualify for.
              </p>
            </div>
          )}
        </TabsContent>

        {/* ── TAB 2: Eligibility History ───────────────────────────────────── */}
        <TabsContent value="history" className="space-y-4">
          {historyLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : history && history.length > 0 ? (
            <Card>
              <CardBody className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Scheme</TableHead>
                      <TableHead>Verdict</TableHead>
                      <TableHead className="hidden md:table-cell">Confidence</TableHead>
                      <TableHead className="hidden lg:table-cell">Explanation</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((r) => (
                      <TableRow key={r.scheme_id}>
                        <TableCell>
                          <div>
                            <p className="font-medium text-sm">{r.scheme_name}</p>
                            <p className="text-xs text-muted-foreground">{r.scheme_id}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Chip size="sm" color={verdictColor(r.verdict)} variant="flat" className="capitalize">
                            {r.verdict}
                          </Chip>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {Math.round(r.confidence * 100)}%
                        </TableCell>
                        <TableCell className="hidden lg:table-cell max-w-xs">
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {r.explanation}
                          </p>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardBody>
            </Card>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FileText className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <h3 className="text-lg font-semibold mb-1">No History Yet</h3>
              <p className="text-sm text-muted-foreground">
                Run an eligibility check to see your results here.
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
