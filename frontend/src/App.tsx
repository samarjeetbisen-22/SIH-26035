import React, { useState, useMemo, useEffect } from "react";
import {
  InstrumentProfile,
  TestConditions,
  ReadingItem,
  AuditHistoryRecord,
} from "./types/metrology";
import {
  DEFAULT_INSTRUMENT,
  DEFAULT_CONDITIONS,
  DEFAULT_READINGS,
  PRESET_PROFILES,
} from "./data/mockData";
import { computeMetrology } from "./utils/oimlEngine";
import {
  checkBackendStatus,
  saveAuditToBackend,
  generateReportLabPdf,
  fetchAuditHistory,
} from "./utils/apiClient";
import { Header } from "./components/Header";
import { InstrumentIntakeForm } from "./components/InstrumentIntakeForm";
import { DataEntryDashboard } from "./components/DataEntryDashboard";
import { ComputationPreview } from "./components/ComputationPreview";
import { AuditHistoryModal } from "./components/AuditHistoryModal";
import {
  CheckCircle2,
  ShieldCheck,
  Scale,
  FileSpreadsheet,
  Sparkles,
  AlertCircle,
} from "lucide-react";

export function App() {
  const [currentTab, setCurrentTab] = useState<"intake" | "testing" | "report">(
    "intake",
  );
  const [instrument, setInstrument] =
    useState<InstrumentProfile>(DEFAULT_INSTRUMENT);
  const [conditions, setConditions] =
    useState<TestConditions>(DEFAULT_CONDITIONS);
  const [readings, setReadings] = useState<ReadingItem[]>(DEFAULT_READINGS);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Backend Integration State
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [isSavingAudit, setIsSavingAudit] = useState<boolean>(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState<boolean>(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);
  const [auditRecords, setAuditRecords] = useState<AuditHistoryRecord[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState<boolean>(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  // Poll / Check Backend Connection
  const checkBackend = async () => {
    const status = await checkBackendStatus();
    setBackendOnline(status.online);
  };

  useEffect(() => {
    checkBackend();
    const interval = setInterval(checkBackend, 10000);
    return () => clearInterval(interval);
  }, []);

  // Live Metrological Calculations Engine
  const computation = useMemo(() => {
    return computeMetrology(instrument, readings);
  }, [instrument, readings]);

  const reportId = `REP-${instrument.accuracyClass}-${instrument.serialNumber.replace(/[^A-Za-z0-9]/g, "").slice(-6)}-2026`;

  // Preset Selector
  const handleSelectPreset = (presetId: string) => {
    const found = PRESET_PROFILES.find((p) => p.id === presetId);
    if (found) {
      setInstrument(found.instrument);
      setConditions(found.conditions);
      setReadings(found.readings);
      showToast(`Loaded preset: ${found.name}`);
    }
  };

  // Reset to Baseline
  const handleReset = () => {
    setInstrument(DEFAULT_INSTRUMENT);
    setConditions(DEFAULT_CONDITIONS);
    setReadings(DEFAULT_READINGS);
    showToast("Reset all test parameters to baseline dataset");
  };

  // Print Certificate (triggers window.print with @media print stylesheet)
  const handlePrint = () => {
    window.print();
  };

  // Backend: Save to SQLite nawi_audit.db
  const handleSaveToAuditDb = async () => {
    setIsSavingAudit(true);
    try {
      const res = await saveAuditToBackend(
        reportId,
        instrument,
        conditions,
        computation,
      );
      if (res.success) {
        showToast("Successfully logged verification audit to nawi_audit.db");
      } else {
        showToast("Could not save to DB: " + (res.message || "Error"));
      }
    } finally {
      setIsSavingAudit(false);
    }
  };

  // Backend: Generate ReportLab PDF via Python
  const handleGeneratePythonPdf = async () => {
    setIsGeneratingPdf(true);
    try {
      const res = await generateReportLabPdf(instrument, conditions, readings);
      if (res.success && res.pdf_url) {
        showToast("Official ReportLab PDF generated. Opening file...");
        window.open(res.pdf_url, "_blank");
      } else {
        showToast(
          "Failed to generate Python PDF: " + (res.error || "Unknown error"),
        );
      }
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  // Open SQLite Audit History Modal
  const handleOpenAuditHistory = async () => {
    setIsAuditModalOpen(true);
    setIsLoadingAudit(true);
    try {
      const records = await fetchAuditHistory();
      setAuditRecords(records);
    } finally {
      setIsLoadingAudit(false);
    }
  };

  // Export JSON Report
  const handleExportJson = () => {
    const exportData = {
      metadata: {
        tool: "Metrolab OIML R-76 Verification Engine",
        version: "2026.1",
        exportedAt: new Date().toISOString(),
        verificationHash: computation.verificationHash,
      },
      instrument,
      test_conditions: conditions,
      readings,
      metrology_evaluation: {
        overall_pass: computation.overallPass,
        compliance_score: computation.complianceScore,
        risk_level: computation.riskLevel,
        combined_uncertainty: computation.combinedUncertainty,
        expanded_uncertainty: computation.expandedUncertainty,
        repeatability_error: computation.repeatabilityError,
        linearity_error: computation.linearityError,
        hysteresis_error: computation.hysteresisError,
        eccentricity_error: computation.eccentricityError,
        point_results: computation.pointResults,
        eccentricity_test: computation.eccentricitySummary,
        repeatability_test: computation.repeatabilitySummary,
      },
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Metrolab_${instrument.model.replace(/\s+/g, "_")}_${instrument.serialNumber}.json`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("Exported official JSON report");
  };

  // Export CSV Ledger
  const handleExportCsv = () => {
    const headers = [
      "Load_kg",
      "Reading_kg",
      "Direction",
      "Repeat_No",
      "Position",
      "Error_kg",
      "MPE_kg",
      "Passed",
    ];
    const rows = computation.pointResults.map((p) => [
      p.load,
      p.reading,
      p.direction,
      p.repeatNumber || 1,
      p.position || "center",
      p.error,
      p.mpe,
      p.passed ? "PASS" : "FAIL",
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((r) => r.join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Metrolab_Readings_${instrument.serialNumber}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("Exported CSV readings ledger");
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] flex flex-col font-sans">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0F172A] text-white text-xs px-4 py-2.5 rounded-md shadow-lg flex items-center space-x-2 border border-slate-700 animate-fade-in no-print">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Top Header & Stage Navigation */}
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        instrument={instrument}
        computation={computation}
        onSelectPreset={handleSelectPreset}
        onReset={handleReset}
        onPrint={handlePrint}
        onExportJson={handleExportJson}
        onExportCsv={handleExportCsv}
        backendOnline={backendOnline}
        onOpenAuditHistory={handleOpenAuditHistory}
      />

      {/* Stage Sub-bar / Step Navigator */}
      <div className="bg-white border-b border-[#E2E8F0] py-2 px-4 sm:px-6 lg:px-8 no-print">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between text-xs text-[#64748B]">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-700">
              Verification Workflow:
            </span>
            <button
              onClick={() => setCurrentTab("intake")}
              className={`hover:underline ${currentTab === "intake" ? "text-blue-600 font-semibold" : ""}`}
            >
              1. Intake Spec
            </button>
            <span>→</span>
            <button
              onClick={() => setCurrentTab("testing")}
              className={`hover:underline ${currentTab === "testing" ? "text-blue-600 font-semibold" : ""}`}
            >
              2. Test Ledger
            </button>
            <span>→</span>
            <button
              onClick={() => setCurrentTab("report")}
              className={`hover:underline ${currentTab === "report" ? "text-blue-600 font-semibold" : ""}`}
            >
              3. Audit Certificate
            </button>
          </div>

          <div className="flex items-center space-x-4">
            <span className="font-mono text-[11px] text-slate-500">
              Active: {instrument.manufacturer} · {instrument.model} (
              {instrument.serialNumber})
            </span>
          </div>
        </div>
      </div>

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {currentTab === "intake" && (
          <InstrumentIntakeForm
            instrument={instrument}
            conditions={conditions}
            onUpdateInstrument={(updates) =>
              setInstrument((prev) => ({ ...prev, ...updates }))
            }
            onUpdateConditions={(updates) =>
              setConditions((prev) => ({ ...prev, ...updates }))
            }
            onProceed={() => {
              setCurrentTab("testing");
              showToast(
                "Instrument profile updated. Proceed to metrological data entry.",
              );
            }}
            onSelectPreset={handleSelectPreset}
          />
        )}

        {currentTab === "testing" && (
          <DataEntryDashboard
            instrument={instrument}
            readings={readings}
            computation={computation}
            onUpdateReadings={setReadings}
            onProceedToReport={() => {
              setCurrentTab("report");
              showToast(
                "Calculations updated. Ready for official report generation.",
              );
            }}
          />
        )}

        {currentTab === "report" && (
          <ComputationPreview
            instrument={instrument}
            conditions={conditions}
            computation={computation}
            readings={readings}
            onPrint={handlePrint}
            onExportJson={handleExportJson}
            onExportCsv={handleExportCsv}
            backendOnline={backendOnline}
            onSaveToAuditDb={handleSaveToAuditDb}
            onGeneratePythonPdf={handleGeneratePythonPdf}
            isSavingAudit={isSavingAudit}
            isGeneratingPdf={isGeneratingPdf}
          />
        )}
      </main>

      {/* SQLite Audit Trail Modal */}
      <AuditHistoryModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
        records={auditRecords}
        isLoading={isLoadingAudit}
        onRefresh={handleOpenAuditHistory}
      />

      {/* Official Lab Footer */}
      <footer className="bg-white border-t border-[#E2E8F0] py-4 text-xs text-[#64748B] no-print">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-700">
              Metrolab NAWI Engine
            </span>
            <span>·</span>
            <span>OIML R 76-1:2006</span>
            <span>·</span>
            <span>The Legal Metrology Act, 2009 (Rule 12 &amp; 24)</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-500">
            <span>Audit Hash: {computation.verificationHash}</span>
            <span>·</span>
            <span>
              Status:{" "}
              {computation.overallPass
                ? "VERIFIED CONFORMING"
                : "NON-CONFORMING"}
            </span>
            <span>·</span>
            <span>
              {backendOnline ? "SQLite Database Connected" : "Browser Engine"}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
