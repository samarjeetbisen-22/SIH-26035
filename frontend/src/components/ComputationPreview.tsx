import React, { useState } from "react";
import {
  InstrumentProfile,
  TestConditions,
  MetrologyComputation,
  ReadingItem,
} from "../types/metrology";
import { OfficialReportDocument } from "./OfficialReportDocument";
import {
  CheckCircle2,
  AlertTriangle,
  Printer,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  TrendingUp,
  Activity,
  ShieldAlert,
  FileCheck,
  Info,
} from "lucide-react";

interface ComputationPreviewProps {
  instrument: InstrumentProfile;
  conditions: TestConditions;
  computation: MetrologyComputation;
  readings: ReadingItem[];
  onPrint: () => void;
  onExportJson: () => void;
  onExportCsv: () => void;
  backendOnline?: boolean;
  onSaveToAuditDb?: () => void;
  onGeneratePythonPdf?: () => void;
  isSavingAudit?: boolean;
  isGeneratingPdf?: boolean;
}

export const ComputationPreview: React.FC<ComputationPreviewProps> = ({
  instrument,
  conditions,
  computation,
  readings,
  onPrint,
  onExportJson,
  onExportCsv,
  backendOnline = false,
  onSaveToAuditDb,
  onGeneratePythonPdf,
  isSavingAudit = false,
  isGeneratingPdf = false,
}) => {
  const [copiedHash, setCopiedHash] = useState(false);
  const [isFullScreenReport, setIsFullScreenReport] = useState(false);
  const [hoveredPointIndex, setHoveredPointIndex] = useState<number | null>(
    null,
  );

  const reportId = `REP-${instrument.accuracyClass}-${instrument.serialNumber.replace(/[^A-Za-z0-9]/g, "").slice(-6)}-2026`;

  const handleCopyHash = () => {
    navigator.clipboard.writeText(computation.verificationHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  // SVG Chart Calculations for Error vs Load
  const chartWidth = 560;
  const chartHeight = 260;
  const padding = { top: 25, right: 30, bottom: 40, left: 60 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const maxCap = Math.max(instrument.maxCapacity, 1);
  const maxMpe = Math.max(
    ...computation.pointResults.map((p) => p.mpe),
    instrument.verificationScaleIntervalE * 1.5,
    0.001,
  );
  const maxErrVal = Math.max(
    ...computation.pointResults.map((p) => Math.abs(p.error)),
    maxMpe * 1.2,
  );

  const scaleX = (val: number) => padding.left + (val / maxCap) * innerWidth;
  const scaleY = (val: number) =>
    padding.top +
    innerHeight / 2 -
    (val / (maxErrVal || 0.001)) * (innerHeight / 2);

  const nonConformingPoints = computation.pointResults.filter((p) => !p.passed);

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 pb-16">
      {/* Top Banner */}
      <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4 no-print">
        <div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-50 text-blue-700 border border-blue-200">
              OIML R 76-1 STATUTORY AUDIT & SYNTHESIS
            </span>
            <span className="text-xs text-[#64748B] font-mono">
              Certificate Ref: {reportId}
            </span>
          </div>
          <h2 className="text-lg font-semibold text-[#0F172A] mt-1">
            Metrological Computation & Official Report Generation
          </h2>
          <p className="text-xs text-[#64748B] mt-0.5">
            Real-time uncertainty budget calculation, step-wise MPE envelope
            verification, and print-ready legal certificate preview.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsFullScreenReport(!isFullScreenReport)}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 transition-colors shadow-subtle"
          >
            {isFullScreenReport ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
            <span>
              {isFullScreenReport ? "Side-by-Side View" : "Full Document View"}
            </span>
          </button>
          <button
            onClick={onPrint}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded transition-colors shadow-subtle"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Official Certificate (A4)</span>
          </button>
        </div>
      </div>

      {/* Side-by-Side View */}
      <div
        className={`grid grid-cols-1 ${isFullScreenReport ? "lg:grid-cols-1" : "lg:grid-cols-12"} gap-6`}
      >
        {/* LEFT COLUMN: Error Computations, Uncertainty Budget & Error Chart */}
        {!isFullScreenReport && (
          <div className="lg:col-span-6 space-y-6 no-print">
            {/* 1. Executive Metrological Verdict Card */}
            <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle">
              <div className="flex items-start justify-between pb-4 border-b border-[#E2E8F0]">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                    Metrological Verification Verdict
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {computation.overallPass ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                    )}
                    <span
                      className={`text-base font-bold tracking-tight ${
                        computation.overallPass
                          ? "text-emerald-700"
                          : "text-red-700"
                      }`}
                    >
                      {computation.overallPass
                        ? "LEGAL METROLOGY CONFORMING"
                        : "NON-CONFORMING / REJECTED"}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={`inline-block px-2.5 py-1 rounded text-xs font-mono font-bold border ${
                      computation.riskLevel === "LOW"
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : computation.riskLevel === "MEDIUM"
                          ? "bg-amber-50 text-amber-800 border-amber-200"
                          : "bg-red-50 text-red-800 border-red-200"
                    }`}
                  >
                    {computation.riskLevel} RISK LEVEL
                  </span>
                </div>
              </div>

              {/* Compliance Score Gauge */}
              <div className="pt-4 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[#64748B]">
                    Overall Health & Compliance Score:
                  </span>
                  <span className="font-mono font-bold text-sm text-[#0F172A]">
                    {computation.complianceScore}%
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      computation.complianceScore >= 90
                        ? "bg-emerald-500"
                        : computation.complianceScore >= 70
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                    style={{ width: `${computation.complianceScore}%` }}
                  />
                </div>
                <p className="text-[11px] text-[#64748B]">
                  Weighted calculation blending 70% average relative error
                  across load spectrum and 30% worst-case test point.
                </p>
              </div>

              {/* Non-conformance alert if any */}
              {nonConformingPoints.length > 0 && (
                <div className="mt-4 p-3 bg-red-50/70 border border-red-200 rounded text-xs space-y-1">
                  <div className="font-semibold text-red-800 flex items-center space-x-1.5">
                    <ShieldAlert className="w-4 h-4 text-red-600" />
                    <span>
                      {nonConformingPoints.length} Point(s) Exceeded OIML R 76-1
                      Limits:
                    </span>
                  </div>
                  <ul className="list-disc list-inside text-red-700 text-[11px] space-y-0.5">
                    {nonConformingPoints.map((pt, i) => (
                      <li key={i} className="font-mono">
                        Load: {pt.load}
                        {instrument.unit} · Reading: {pt.reading}
                        {instrument.unit} · Error: {pt.error > 0 ? "+" : ""}
                        {pt.error.toFixed(4)} (MPE: ±{pt.mpe.toFixed(4)})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* 2. Interactive SVG Error Curve vs OIML Step MPE Envelopes */}
            <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle">
              <div className="flex items-center justify-between pb-3 mb-2 border-b border-[#E2E8F0]">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[#0F172A]">
                    Indication Error vs Load Profile (OIML R-76 MPE Envelopes)
                  </h3>
                  <p className="text-[11px] text-[#64748B]">
                    Plot showing actual measurement deviations vs step-function
                    permissible boundaries
                  </p>
                </div>
                <div className="flex items-center space-x-3 text-[10px] font-mono">
                  <span className="flex items-center space-x-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                    <span>Pass</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                    <span>Fail</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <span className="w-3 h-0.5 bg-blue-400"></span>
                    <span>±MPE Limit</span>
                  </span>
                </div>
              </div>

              {/* The SVG Visualization */}
              <div className="overflow-x-auto">
                <svg
                  width={chartWidth}
                  height={chartHeight}
                  className="font-mono text-[9px] select-none mx-auto"
                >
                  {/* Grid Lines */}
                  <line
                    x1={padding.left}
                    y1={scaleY(0)}
                    x2={chartWidth - padding.right}
                    y2={scaleY(0)}
                    stroke="#94A3B8"
                    strokeWidth="1"
                    strokeDasharray="2,2"
                  />
                  <line
                    x1={padding.left}
                    y1={padding.top}
                    x2={padding.left}
                    y2={chartHeight - padding.bottom}
                    stroke="#CBD5E1"
                    strokeWidth="1"
                  />
                  <line
                    x1={padding.left}
                    y1={chartHeight - padding.bottom}
                    x2={chartWidth - padding.right}
                    y2={chartHeight - padding.bottom}
                    stroke="#CBD5E1"
                    strokeWidth="1"
                  />

                  {/* Axis Labels */}
                  <text
                    x={padding.left - 8}
                    y={padding.top + 4}
                    textAnchor="end"
                    fill="#64748B"
                  >
                    +{maxErrVal.toFixed(3)}
                  </text>
                  <text
                    x={padding.left - 8}
                    y={scaleY(0) + 3}
                    textAnchor="end"
                    fill="#64748B"
                  >
                    0.000
                  </text>
                  <text
                    x={padding.left - 8}
                    y={chartHeight - padding.bottom}
                    textAnchor="end"
                    fill="#64748B"
                  >
                    -{maxErrVal.toFixed(3)}
                  </text>

                  <text
                    x={padding.left}
                    y={chartHeight - padding.bottom + 16}
                    textAnchor="middle"
                    fill="#64748B"
                  >
                    0
                  </text>
                  <text
                    x={scaleX(maxCap * 0.5)}
                    y={chartHeight - padding.bottom + 16}
                    textAnchor="middle"
                    fill="#64748B"
                  >
                    {(maxCap * 0.5).toFixed(1)} {instrument.unit}
                  </text>
                  <text
                    x={scaleX(maxCap)}
                    y={chartHeight - padding.bottom + 16}
                    textAnchor="middle"
                    fill="#64748B"
                  >
                    {maxCap.toFixed(1)} {instrument.unit} (Max)
                  </text>

                  {/* Draw MPE Envelope Bands (Upper & Lower) */}
                  {computation.pointResults
                    .sort((a, b) => a.load - b.load)
                    .map((p, idx, arr) => {
                      if (idx === 0) return null;
                      const prev = arr[idx - 1];
                      return (
                        <g key={`mpe-band-${idx}`}>
                          {/* Upper Limit Segment */}
                          <line
                            x1={scaleX(prev.load)}
                            y1={scaleY(prev.mpe)}
                            x2={scaleX(p.load)}
                            y2={scaleY(p.mpe)}
                            stroke="#3B82F6"
                            strokeWidth="1.5"
                            strokeDasharray="4,2"
                          />
                          {/* Lower Limit Segment */}
                          <line
                            x1={scaleX(prev.load)}
                            y1={scaleY(-prev.mpe)}
                            x2={scaleX(p.load)}
                            y2={scaleY(-p.mpe)}
                            stroke="#3B82F6"
                            strokeWidth="1.5"
                            strokeDasharray="4,2"
                          />
                        </g>
                      );
                    })}

                  {/* Data Point Error Line */}
                  {computation.pointResults
                    .filter(
                      (p) =>
                        p.direction === "increasing" &&
                        (p.position === "center" || !p.position),
                    )
                    .sort((a, b) => a.load - b.load)
                    .map((p, idx, arr) => {
                      if (idx === 0) return null;
                      const prev = arr[idx - 1];
                      return (
                        <line
                          key={`data-line-${idx}`}
                          x1={scaleX(prev.load)}
                          y1={scaleY(prev.error)}
                          x2={scaleX(p.load)}
                          y2={scaleY(p.error)}
                          stroke="#0F172A"
                          strokeWidth="1.2"
                        />
                      );
                    })}

                  {/* Data Circles */}
                  {computation.pointResults.map((p, idx) => {
                    const cx = scaleX(p.load);
                    const cy = scaleY(p.error);
                    const isHovered = hoveredPointIndex === idx;

                    return (
                      <g
                        key={`pt-${idx}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredPointIndex(idx)}
                        onMouseLeave={() => setHoveredPointIndex(null)}
                      >
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isHovered ? 5.5 : 3.5}
                          fill={p.passed ? "#059669" : "#DC2626"}
                          stroke="#FFFFFF"
                          strokeWidth="1.5"
                        />
                        {isHovered && (
                          <g>
                            <rect
                              x={Math.min(
                                chartWidth - 110,
                                Math.max(10, cx - 45),
                              )}
                              y={Math.max(10, cy - 35)}
                              width="90"
                              height="26"
                              rx="3"
                              fill="#0F172A"
                              opacity="0.9"
                            />
                            <text
                              x={
                                Math.min(
                                  chartWidth - 110,
                                  Math.max(10, cx - 45),
                                ) + 45
                              }
                              y={Math.max(10, cy - 35) + 11}
                              textAnchor="middle"
                              fill="#FFFFFF"
                              fontSize="8"
                              fontWeight="bold"
                            >
                              Load: {p.load}
                              {instrument.unit}
                            </text>
                            <text
                              x={
                                Math.min(
                                  chartWidth - 110,
                                  Math.max(10, cx - 45),
                                ) + 45
                              }
                              y={Math.max(10, cy - 35) + 21}
                              textAnchor="middle"
                              fill={p.passed ? "#34D399" : "#F87171"}
                              fontSize="8"
                            >
                              Err: {p.error > 0 ? "+" : ""}
                              {p.error.toFixed(4)} ({p.passed ? "PASS" : "FAIL"}
                              )
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* 3. Metrological Uncertainty Budget (ISO/IEC Guide 98-3 / GUM) */}
            <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle">
              <div className="flex items-center space-x-2 pb-3 mb-3 border-b border-[#E2E8F0]">
                <Activity className="w-4 h-4 text-blue-600" />
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[#0F172A]">
                    Metrological Uncertainty Budget (GUM / OIML Guide)
                  </h3>
                  <p className="text-[11px] text-[#64748B]">
                    Constituent standard uncertainty components synthesized via
                    root-sum-of-squares (RSS)
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="grid grid-cols-3 p-2 bg-slate-50 border border-slate-200 rounded font-medium text-slate-700">
                  <span>Uncertainty Source</span>
                  <span className="text-right">Relative Error (s/Cap)</span>
                  <span className="text-right">Absolute (kg/unit)</span>
                </div>

                <div className="grid grid-cols-3 px-2 py-1.5 border-b border-slate-100 font-mono text-[11px]">
                  <span className="font-sans text-slate-700">
                    Repeatability (u_rep)
                  </span>
                  <span className="text-right text-slate-600">
                    {computation.repeatabilityError.toFixed(6)}
                  </span>
                  <span className="text-right font-medium text-slate-800">
                    {(
                      computation.repeatabilityError * instrument.maxCapacity
                    ).toFixed(5)}{" "}
                    {instrument.unit}
                  </span>
                </div>

                <div className="grid grid-cols-3 px-2 py-1.5 border-b border-slate-100 font-mono text-[11px]">
                  <span className="font-sans text-slate-700">
                    Linearity / Dev (u_lin)
                  </span>
                  <span className="text-right text-slate-600">
                    {computation.linearityError.toFixed(6)}
                  </span>
                  <span className="text-right font-medium text-slate-800">
                    {(
                      computation.linearityError * instrument.maxCapacity
                    ).toFixed(5)}{" "}
                    {instrument.unit}
                  </span>
                </div>

                <div className="grid grid-cols-3 px-2 py-1.5 border-b border-slate-100 font-mono text-[11px]">
                  <span className="font-sans text-slate-700">
                    Eccentricity (u_ecc)
                  </span>
                  <span className="text-right text-slate-600">
                    {computation.eccentricityError.toFixed(6)}
                  </span>
                  <span className="text-right font-medium text-slate-800">
                    {(
                      computation.eccentricityError * instrument.maxCapacity
                    ).toFixed(5)}{" "}
                    {instrument.unit}
                  </span>
                </div>

                <div className="grid grid-cols-3 px-2 py-1.5 border-b border-slate-100 font-mono text-[11px]">
                  <span className="font-sans text-slate-700">
                    Hysteresis (u_hyst)
                  </span>
                  <span className="text-right text-slate-600">
                    {computation.hysteresisError.toFixed(6)}
                  </span>
                  <span className="text-right font-medium text-slate-800">
                    {(
                      computation.hysteresisError * instrument.maxCapacity
                    ).toFixed(5)}{" "}
                    {instrument.unit}
                  </span>
                </div>

                {/* Combined Uncertainty */}
                <div className="grid grid-cols-3 p-2 bg-blue-50/60 border border-blue-200 rounded font-mono text-[11px] font-semibold text-blue-900 mt-2">
                  <span className="font-sans">
                    Combined Standard Uncertainty (u_c)
                  </span>
                  <span className="text-right">
                    {computation.combinedUncertainty.toFixed(6)}
                  </span>
                  <span className="text-right">
                    {(
                      computation.combinedUncertainty * instrument.maxCapacity
                    ).toFixed(5)}{" "}
                    {instrument.unit}
                  </span>
                </div>

                {/* Expanded Uncertainty */}
                <div className="grid grid-cols-3 p-2 bg-slate-900 text-white rounded font-mono text-[11px] font-semibold mt-1">
                  <span className="font-sans">
                    Expanded Uncertainty U (k=2, 95% CL)
                  </span>
                  <span className="text-right">
                    {computation.expandedUncertainty.toFixed(6)}
                  </span>
                  <span className="text-right text-emerald-400">
                    ±
                    {(
                      computation.expandedUncertainty * instrument.maxCapacity
                    ).toFixed(5)}{" "}
                    {instrument.unit}
                  </span>
                </div>
              </div>

              {/* Verification Hash Card */}
              <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between text-xs">
                <div>
                  <span className="text-[#64748B] block text-[10px]">
                    Statutory Verification Hash:
                  </span>
                  <span className="font-mono text-slate-800 font-medium">
                    {computation.verificationHash}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyHash}
                  className="flex items-center space-x-1 px-2.5 py-1 text-xs rounded border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                >
                  {copiedHash ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  <span>{copiedHash ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* RIGHT COLUMN: Official Document Preview */}
        <div className={isFullScreenReport ? "col-span-12" : "lg:col-span-6"}>
          {/* Header controls for Document Sheet */}
          <div className="flex items-center justify-between mb-3 no-print">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#0F172A]">
                Official Legal Metrology Test Report
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                PDF Ready
              </span>
            </div>

            <div className="flex items-center space-x-1.5 text-xs flex-wrap gap-y-1">
              {backendOnline && onSaveToAuditDb && (
                <button
                  onClick={onSaveToAuditDb}
                  disabled={isSavingAudit}
                  className="px-2.5 py-1 rounded border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 font-medium transition-colors"
                  title="Persist record to SQLite database nawi_audit.db"
                >
                  {isSavingAudit ? "Saving..." : "💾 Save to DB"}
                </button>
              )}
              {backendOnline && onGeneratePythonPdf && (
                <button
                  onClick={onGeneratePythonPdf}
                  disabled={isGeneratingPdf}
                  className="px-2.5 py-1 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 font-medium transition-colors"
                  title="Generate Python ReportLab PDF with QR code"
                >
                  {isGeneratingPdf ? "Generating..." : "📄 Python PDF"}
                </button>
              )}
              <button
                onClick={onExportCsv}
                className="px-2.5 py-1 rounded border border-[#E2E8F0] bg-white text-slate-700 hover:bg-slate-50 font-medium"
              >
                CSV
              </button>
              <button
                onClick={onExportJson}
                className="px-2.5 py-1 rounded border border-[#E2E8F0] bg-white text-slate-700 hover:bg-slate-50 font-medium"
              >
                JSON
              </button>
              <button
                onClick={onPrint}
                className="flex items-center space-x-1.5 px-3 py-1 text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded font-medium shadow-subtle"
              >
                <Printer className="w-3 h-3" />
                <span>Print Document</span>
              </button>
            </div>
          </div>

          {/* Document Renderer */}
          <div className="bg-slate-100/70 p-4 sm:p-6 rounded-lg border border-[#E2E8F0] overflow-x-auto shadow-inner">
            <OfficialReportDocument
              instrument={instrument}
              conditions={conditions}
              computation={computation}
              reportId={reportId}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
