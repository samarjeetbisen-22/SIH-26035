import React from "react";
import {
  Scale,
  FileCheck2,
  SlidersHorizontal,
  FileText,
  Printer,
  Download,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  Database,
  Paperclip,
} from "lucide-react";
import { InstrumentProfile, MetrologyComputation } from "../types/metrology";
import { PRESET_PROFILES } from "../data/mockData";

interface HeaderProps {
  currentTab: "intake" | "testing" | "report";
  onTabChange: (tab: "intake" | "testing" | "report") => void;
  instrument: InstrumentProfile;
  computation: MetrologyComputation;
  onSelectPreset: (presetId: string) => void;
  onReset: () => void;
  onPrint: () => void;
  onExportJson: () => void;
  onExportCsv: () => void;
  backendOnline: boolean;
  onOpenAuditHistory: () => void;
  onOpenAttachments?: () => void;
  evaluationId?: string | null;
  evaluationStatus?: string;
  onNewEvaluation?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  instrument,
  computation,
  onSelectPreset,
  onReset,
  onPrint,
  onExportJson,
  onExportCsv,
  backendOnline,
  onOpenAuditHistory,
  onOpenAttachments,
  evaluationId,
  evaluationStatus,
  onNewEvaluation,
}) => {
  const [presetDropdownOpen, setPresetDropdownOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-40 bg-[#FFFFFF] border-b border-[#E2E8F0] shadow-subtle no-print">
      {/* Top Banner: Enterprise Identity & Quick Status */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Lab System Branding */}
          <div className="flex items-center space-x-3.5">
            <div className="w-9 h-9 rounded bg-[#2563EB] flex items-center justify-center text-white shadow-sm ring-1 ring-blue-700/10">
              <Scale className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-[17px] tracking-tight text-[#0F172A] font-sans">
                  METROLAB
                </span>
                <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  OIML R 76-1:2006
                </span>
                <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  LEGAL METROLOGY ACT 2009
                </span>
              </div>
              <p className="text-xs text-[#64748B]">
                Digital Testing & Statutory Compliance Engine for NAWIs
              </p>
            </div>
          </div>

          {/* Active Instrument Pill & Quick Preset Switcher */}
          <div className="hidden lg:flex items-center space-x-4">
            <div className="relative">
              <button
                type="button"
                onClick={() => setPresetDropdownOpen(!presetDropdownOpen)}
                className="flex items-center space-x-2.5 px-3 py-1.5 text-xs font-medium text-[#0F172A] bg-white border border-[#E2E8F0] rounded hover:border-slate-300 transition-colors shadow-subtle"
              >
                <div className="flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                  <span className="font-mono text-slate-500">Preset:</span>
                  <span className="font-medium truncate max-w-[200px]">
                    {instrument.model}
                  </span>
                </div>
                <span className="px-1.5 py-0.2 rounded bg-slate-100 text-[10px] font-mono text-slate-600 border border-slate-200">
                  Class {instrument.accuracyClass}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {presetDropdownOpen && (
                <div
                  className="absolute right-0 mt-1.5 w-80 bg-white border border-[#E2E8F0] rounded-md shadow-lg py-1.5 z-50"
                  onMouseLeave={() => setPresetDropdownOpen(false)}
                >
                  <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#64748B] border-b border-slate-100">
                    Load Metrology Test Case
                  </div>
                  {PRESET_PROFILES.map((preset) => (
                    <button
                      key={preset.id}
                      onClick={() => {
                        onSelectPreset(preset.id);
                        setPresetDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 flex items-center justify-between border-b border-slate-50 last:border-0"
                    >
                      <div>
                        <div className="font-medium text-[#0F172A]">
                          {preset.name}
                        </div>
                        <div className="text-[11px] text-[#64748B] font-mono">
                          {preset.instrument.serialNumber}
                        </div>
                      </div>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">
                        {preset.classTag}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Metrological Compliance Quick Indicator */}
            <div
              className={`flex items-center space-x-2 px-3 py-1 rounded text-xs font-mono font-medium border ${
                computation.overallPass
                  ? "bg-[#ECFDF5] text-[#059669] border-emerald-200"
                  : "bg-[#FEF2F2] text-[#DC2626] border-red-200"
              }`}
            >
              {computation.overallPass ? (
                <CheckCircle2 className="w-3.5 h-3.5" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5" />
              )}
              <span>
                {computation.overallPass
                  ? "VERIFIED CONFORMING"
                  : "NON-CONFORMING"}
              </span>
              <span className="text-slate-400">|</span>
              <span>Score: {computation.complianceScore}%</span>
            </div>

            {/* Active Evaluation ID & Workflow Status */}
            {evaluationId ? (
              <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-mono font-medium bg-blue-50 border border-blue-200 text-blue-800">
                <span className="text-slate-500 font-normal">Eval:</span>
                <span className="font-bold">{evaluationId.length > 15 ? evaluationId.slice(0, 15) + "…" : evaluationId}</span>
                <span className={`text-[10px] px-1 py-0.5 rounded uppercase font-semibold ${
                  evaluationStatus === 'APPROVED' ? 'bg-emerald-100 text-emerald-800' :
                  evaluationStatus === 'SUBMITTED' ? 'bg-amber-100 text-amber-800' :
                  'bg-white border border-blue-200 text-blue-700'
                }`}>
                  {evaluationStatus || 'DRAFT'}
                </span>
              </div>
            ) : (
              <div className="flex items-center space-x-1 px-2 py-1 rounded text-xs font-mono text-slate-500 bg-slate-50 border border-slate-200">
                <span>Unsaved Draft</span>
              </div>
            )}

            {/* Backend Integration Status Indicator */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-[11px] font-mono border ${
                backendOnline
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-slate-50 text-slate-500 border-slate-200"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${backendOnline ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`}
              ></span>
              <span>
                {backendOnline ? "Python Bridge: 8000" : "Standalone"}
              </span>
            </div>
          </div>

          {/* Quick Actions (Print, Export, Reset, Audit DB) */}
          <div className="flex items-center space-x-2">
            {onNewEvaluation && (
              <button
                onClick={onNewEvaluation}
                title="Start a new clean evaluation"
                className="flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors shadow-subtle"
              >
                <span>+ New Eval</span>
              </button>
            )}
            <button
              onClick={onOpenAuditHistory}
              title="Open SQLite Audit Trail (nawi_audit.db)"
              className="flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 transition-colors shadow-subtle"
            >
              <Database className="w-3.5 h-3.5 text-blue-600" />
              <span className="hidden sm:inline">Audit DB</span>
            </button>
            {onOpenAttachments && (
              <button
                onClick={onOpenAttachments}
                title="Evidence & Calibration Certificate Attachments"
                className="flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 transition-colors shadow-subtle"
              >
                <Paperclip className="w-3.5 h-3.5 text-blue-600" />
                <span className="hidden sm:inline">Attachments</span>
              </button>
            )}
            <div className="h-4 w-px bg-slate-200"></div>
            <button
              onClick={onReset}
              title="Reset test data to defaults"
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded border border-transparent hover:border-slate-200 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={onExportCsv}
              className="hidden sm:inline-flex items-center space-x-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>CSV</span>
            </button>
            <button
              onClick={onExportJson}
              className="hidden sm:inline-flex items-center space-x-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>JSON</span>
            </button>
            <button
              onClick={onPrint}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded transition-colors shadow-subtle"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Certificate</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation: Workflow Stages */}
        <div className="flex space-x-1 border-t border-[#E2E8F0]">
          <button
            onClick={() => onTabChange("intake")}
            className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all ${
              currentTab === "intake"
                ? "border-[#2563EB] text-[#2563EB] font-semibold bg-blue-50/30"
                : "border-transparent text-[#64748B] hover:text-[#0F172A] hover:bg-slate-50"
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>1. Instrument Profiling & Intake</span>
            <span className="text-[10px] font-mono px-1 rounded bg-slate-100 text-slate-600">
              Class {instrument.accuracyClass}
            </span>
          </button>

          <button
            onClick={() => onTabChange("testing")}
            className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all ${
              currentTab === "testing"
                ? "border-[#2563EB] text-[#2563EB] font-semibold bg-blue-50/30"
                : "border-transparent text-[#64748B] hover:text-[#0F172A] hover:bg-slate-50"
            }`}
          >
            <FileCheck2 className="w-3.5 h-3.5" />
            <span>2. Testing & Metrological Data Entry</span>
            <span className="text-[10px] font-mono px-1 rounded bg-slate-100 text-slate-600">
              {computation.pointResults.length} readings
            </span>
          </button>

          <button
            onClick={() => onTabChange("report")}
            className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all ${
              currentTab === "report"
                ? "border-[#2563EB] text-[#2563EB] font-semibold bg-blue-50/30"
                : "border-transparent text-[#64748B] hover:text-[#0F172A] hover:bg-slate-50"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>3. Computation & Report Preview</span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-medium ${
                computation.overallPass
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-red-50 text-red-700"
              }`}
            >
              {computation.overallPass ? "PASS" : "FAIL"}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
};
