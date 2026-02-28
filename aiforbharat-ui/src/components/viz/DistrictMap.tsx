"use client";

import { useState, useMemo, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import { scaleLinear } from "d3-scale";
import { MapPin, Info, ZoomIn, ZoomOut } from "lucide-react";

import { Card, CardBody, CardHeader, Chip, Divider } from "@nextui-org/react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * DistrictMap — India geospatial heatmap component.
 *
 * Uses react-simple-maps (mapcn alternative) to render an interactive
 * India choropleth map with demographic/NFHS-5 style statistics.
 *
 * Features:
 *  - Choropleth coloring by metric (population, schemes, literacy, etc.)
 *  - Hover tooltip with state-level details
 *  - Zoom + pan controls
 *  - Metric selector
 *
 * TopoJSON: Natural Earth India admin-1 (states/UTs)
 * Libraries: react-simple-maps, d3-scale, Hero UI, ShadCN
 */

const INDIA_TOPO_URL =
  "https://cdn.jsdelivr.net/npm/india-topojson@1.0.0/india.json";

// ── Sample state-level data (NFHS-5 style metrics) ──────────────────────────

interface StateMetric {
  name: string;
  population: number;
  schemesActive: number;
  literacyRate: number;
  beneficiaries: number;
  trustAvg: number;
}

const STATE_DATA: Record<string, StateMetric> = {
  "Uttar Pradesh":       { name: "Uttar Pradesh",       population: 199812, schemesActive: 342, literacyRate: 73.0, beneficiaries: 45200, trustAvg: 68 },
  "Maharashtra":         { name: "Maharashtra",         population: 112374, schemesActive: 298, literacyRate: 82.9, beneficiaries: 38100, trustAvg: 74 },
  "Bihar":               { name: "Bihar",               population: 104099, schemesActive: 256, literacyRate: 63.8, beneficiaries: 31000, trustAvg: 59 },
  "West Bengal":         { name: "West Bengal",         population: 91276,  schemesActive: 278, literacyRate: 77.1, beneficiaries: 28500, trustAvg: 65 },
  "Madhya Pradesh":      { name: "Madhya Pradesh",      population: 72627,  schemesActive: 265, literacyRate: 69.3, beneficiaries: 24800, trustAvg: 62 },
  "Tamil Nadu":          { name: "Tamil Nadu",          population: 72147,  schemesActive: 312, literacyRate: 80.1, beneficiaries: 32100, trustAvg: 76 },
  "Rajasthan":           { name: "Rajasthan",           population: 68548,  schemesActive: 245, literacyRate: 66.1, beneficiaries: 22400, trustAvg: 61 },
  "Karnataka":           { name: "Karnataka",           population: 61095,  schemesActive: 289, literacyRate: 75.4, beneficiaries: 27300, trustAvg: 72 },
  "Gujarat":             { name: "Gujarat",             population: 60440,  schemesActive: 271, literacyRate: 79.3, beneficiaries: 25600, trustAvg: 70 },
  "Andhra Pradesh":      { name: "Andhra Pradesh",      population: 49577,  schemesActive: 234, literacyRate: 67.4, beneficiaries: 19800, trustAvg: 66 },
  "Odisha":              { name: "Odisha",              population: 41974,  schemesActive: 228, literacyRate: 72.9, beneficiaries: 18200, trustAvg: 63 },
  "Telangana":           { name: "Telangana",           population: 35004,  schemesActive: 256, literacyRate: 72.8, beneficiaries: 16500, trustAvg: 69 },
  "Kerala":              { name: "Kerala",              population: 33406,  schemesActive: 305, literacyRate: 96.2, beneficiaries: 21200, trustAvg: 82 },
  "Jharkhand":           { name: "Jharkhand",           population: 32988,  schemesActive: 198, literacyRate: 66.4, beneficiaries: 14600, trustAvg: 58 },
  "Assam":               { name: "Assam",               population: 31206,  schemesActive: 187, literacyRate: 72.2, beneficiaries: 12800, trustAvg: 60 },
  "Punjab":              { name: "Punjab",              population: 27743,  schemesActive: 232, literacyRate: 75.8, beneficiaries: 15400, trustAvg: 71 },
  "Chhattisgarh":        { name: "Chhattisgarh",        population: 25545,  schemesActive: 212, literacyRate: 70.3, beneficiaries: 11900, trustAvg: 64 },
  "Haryana":             { name: "Haryana",             population: 25351,  schemesActive: 241, literacyRate: 75.6, beneficiaries: 14200, trustAvg: 69 },
  "Delhi":               { name: "Delhi",               population: 16788,  schemesActive: 198, literacyRate: 86.2, beneficiaries: 9800,  trustAvg: 73 },
  "Jammu and Kashmir":   { name: "Jammu and Kashmir",   population: 12267,  schemesActive: 176, literacyRate: 67.2, beneficiaries: 7200,  trustAvg: 62 },
  "Uttarakhand":         { name: "Uttarakhand",         population: 10086,  schemesActive: 195, literacyRate: 78.8, beneficiaries: 6400,  trustAvg: 68 },
  "Himachal Pradesh":    { name: "Himachal Pradesh",    population: 6864,   schemesActive: 204, literacyRate: 82.8, beneficiaries: 5100,  trustAvg: 75 },
  "Tripura":             { name: "Tripura",             population: 3673,   schemesActive: 156, literacyRate: 87.2, beneficiaries: 2800,  trustAvg: 67 },
  "Meghalaya":           { name: "Meghalaya",           population: 2967,   schemesActive: 142, literacyRate: 74.4, beneficiaries: 2100,  trustAvg: 61 },
  "Manipur":             { name: "Manipur",             population: 2855,   schemesActive: 138, literacyRate: 76.9, beneficiaries: 1900,  trustAvg: 60 },
  "Nagaland":            { name: "Nagaland",            population: 1978,   schemesActive: 125, literacyRate: 80.1, beneficiaries: 1400,  trustAvg: 63 },
  "Goa":                 { name: "Goa",                 population: 1458,   schemesActive: 168, literacyRate: 88.7, beneficiaries: 1200,  trustAvg: 78 },
  "Arunachal Pradesh":   { name: "Arunachal Pradesh",   population: 1383,   schemesActive: 132, literacyRate: 65.4, beneficiaries: 980,   trustAvg: 57 },
  "Mizoram":             { name: "Mizoram",             population: 1097,   schemesActive: 128, literacyRate: 91.3, beneficiaries: 820,   trustAvg: 72 },
  "Sikkim":              { name: "Sikkim",              population: 610,    schemesActive: 145, literacyRate: 81.4, beneficiaries: 520,   trustAvg: 70 },
};

// ── Metric configurations ───────────────────────────────────────────────────

type MetricKey = "population" | "schemesActive" | "literacyRate" | "beneficiaries" | "trustAvg";

const METRICS: Array<{ key: MetricKey; label: string; format: (v: number) => string; colorRange: [string, string] }> = [
  { key: "schemesActive",  label: "Active Schemes",     format: (v) => `${v}`,              colorRange: ["#dbeafe", "#1d4ed8"] },
  { key: "beneficiaries",  label: "Beneficiaries",      format: (v) => `${(v / 1000).toFixed(1)}K`, colorRange: ["#dcfce7", "#15803d"] },
  { key: "literacyRate",   label: "Literacy Rate (%)",   format: (v) => `${v.toFixed(1)}%`,   colorRange: ["#fef9c3", "#a16207"] },
  { key: "trustAvg",       label: "Avg Trust Score",     format: (v) => `${v}/100`,           colorRange: ["#ede9fe", "#7c3aed"] },
  { key: "population",     label: "Population (000s)",   format: (v) => `${(v / 1000).toFixed(0)}M`, colorRange: ["#fee2e2", "#b91c1c"] },
];

// ── Component ───────────────────────────────────────────────────────────────

interface DistrictMapProps {
  className?: string;
}

function DistrictMapInner({ className }: DistrictMapProps) {
  const [metric, setMetric] = useState<MetricKey>("schemesActive");
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  const metricConfig = METRICS.find((m) => m.key === metric) ?? METRICS[0];

  // Build color scale
  const colorScale = useMemo(() => {
    const values = Object.values(STATE_DATA).map((d) => d[metric]);
    return scaleLinear<string>()
      .domain([Math.min(...values), Math.max(...values)])
      .range(metricConfig.colorRange);
  }, [metric, metricConfig]);

  const hoveredData = hoveredState ? STATE_DATA[hoveredState] : null;

  return (
    <Card className={`border border-border/40 overflow-hidden ${className ?? ""}`}>
      <CardHeader className="pb-2 flex flex-row items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <MapPin className="h-5 w-5 text-chart-1" />
          <h3 className="text-base font-semibold">India — District Map</h3>
        </div>
        <div className="flex items-center gap-2">
          <Select value={metric} onValueChange={(v) => setMetric(v as MetricKey)}>
            <SelectTrigger className="h-8 w-[160px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {METRICS.map((m) => (
                <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.min(z * 1.3, 4))}>
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.max(z / 1.3, 0.5))}>
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardBody className="p-0 relative">
        <div className="h-[450px] w-full">
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ scale: 900, center: [82, 22] }}
            className="w-full h-full"
          >
            <ZoomableGroup zoom={zoom} onMoveEnd={({ zoom: z }) => setZoom(z)}>
              <Geographies geography={INDIA_TOPO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const stateName = geo.properties.NAME_1 || geo.properties.name || geo.properties.ST_NM;
                    const stateData = STATE_DATA[stateName];
                    const value = stateData ? stateData[metric] : 0;
                    const isHovered = hoveredState === stateName;

                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={stateData ? colorScale(value) : "#e5e7eb"}
                        stroke="hsl(var(--border))"
                        strokeWidth={isHovered ? 1.5 : 0.5}
                        style={{
                          default: { outline: "none", transition: "fill 0.2s" },
                          hover: { outline: "none", fill: "#60a5fa", cursor: "pointer" },
                          pressed: { outline: "none" },
                        }}
                        onMouseEnter={() => setHoveredState(stateName)}
                        onMouseLeave={() => setHoveredState(null)}
                      />
                    );
                  })
                }
              </Geographies>
            </ZoomableGroup>
          </ComposableMap>
        </div>

        {/* Color Legend */}
        <div className="absolute bottom-3 left-3 flex items-center gap-2 bg-card/90 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-border text-[10px]">
          <span className="text-muted-foreground">Low</span>
          <div
            className="h-2.5 w-24 rounded-full"
            style={{
              background: `linear-gradient(90deg, ${metricConfig.colorRange[0]}, ${metricConfig.colorRange[1]})`,
            }}
          />
          <span className="text-muted-foreground">High</span>
        </div>

        {/* Hover Tooltip */}
        <AnimatePresence>
          {hoveredData && (
            <motion.div
              key="map-tooltip"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.1, ease: "easeOut" }}
              className="absolute top-3 right-3 bg-card border border-border rounded-lg shadow-lg p-3 min-w-[180px] pointer-events-none"
            >
            <p className="text-sm font-semibold mb-1">{hoveredData.name}</p>
            <Divider className="my-1.5" />
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Active Schemes</span>
                <span className="font-medium">{hoveredData.schemesActive}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Beneficiaries</span>
                <span className="font-medium">{(hoveredData.beneficiaries / 1000).toFixed(1)}K</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Literacy Rate</span>
                <span className="font-medium">{hoveredData.literacyRate}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Trust Score</span>
                <Chip size="sm" variant="flat" color={hoveredData.trustAvg >= 70 ? "success" : hoveredData.trustAvg >= 50 ? "warning" : "danger"}>
                  {hoveredData.trustAvg}/100
                </Chip>
              </div>
            </div>
          </motion.div>
          )}
        </AnimatePresence>
      </CardBody>
    </Card>
  );
}

const DistrictMap = memo(DistrictMapInner);
export default DistrictMap;
