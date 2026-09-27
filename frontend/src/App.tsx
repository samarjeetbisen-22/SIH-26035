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
  getAuthUser,
  setAuthUser,
  loginUser,
  fetchDashboardStats,
  UserSession,
} from "./utils/apiClient";
import { Header } from "./components/Header";
import { AuthRoleSwitcher } from "./components/AuthRoleSwitcher";
import { InstrumentIntakeForm } from "./components/InstrumentIntakeForm";
import { DataEntryDashboard } from "./components/DataEntryDashboard";
import { ComputationPreview } from "./components/ComputationPreview";
import { AuditHistoryModal } from "./components/AuditHistoryModal";
import { ReviewerQueueModal } from "./components/ReviewerQueueModal";
import { OwnerPortalModal } from "./components/OwnerPortalModal";
import { AttachmentUploadModal } from "./components/AttachmentUploadModal";
import {
  ShieldCheck,
  Building,
  Paperclip,
  Activity,
  Layers,
  CheckCircle2,
  AlertTriangle,
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

  // Authentication State
  const [currentUser, setCurrentUser] = useState<UserSession | null>(
    getAuthUser(),
  );

  // Backend Integration & Modals State
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [isSavingAudit, setIsSavingAudit] = useState<boolean>(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState<boolean>(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);
  const [isReviewerModalOpen, setIsReviewerModalOpen] =
    useState<boolean>(false);
  const [isOwnerModalOpen, setIsOwnerModalOpen] = useState<boolean>(false);
  const [isAttachmentModalOpen, setIsAttachmentModalOpen] =
    useState<boolean>(false);
  const [auditRecords, setAuditRecords] = useState<AuditHistoryRecord[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState<boolean>(false);
  const [dashboardStats, setDashboardStats] = useState<any | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  // Check Backend Connection & Poll Dashboard Stats
  const checkBackend = async () => {
    const status = await checkBackendStatus();
    setBackendOnline(status.online);
    if (status.online) {
      const stats = await fetchDashboardStats();
      if (stats) setDashboardStats(stats);
    }
  };

  useEffect(() => {
    checkBackend();
    const interval = setInterval(checkBackend, 10000);

    // If not authenticated yet, default login as Inspector
    if (!currentUser) {
      loginUser("rajesh_inspector", "Inspector@123").then((res) => {
        if (res.success && res.user) {
          setCurrentUser(res.user);
        }
      });
    }

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
        checkBackend();
      } else {
        showToast("Could not save to DB: " + (res.message || "Error"));
      }
    } finally {
      setIsSavingAudit(false);
    }
  };

  // Backend: Official ReportLab PDF
  const handleGeneratePythonPdf = async () => {
    setIsGeneratingPdf(true);
    try {
      const res = await generateReportLabPdf(instrument, conditions, readings);
      if (res.success && res.pdf_url) {
        showToast("Generated official Python ReportLab PDF!");
        window.open(res.pdf_url, "_blank");
      } else {
        showToast("PDF generation failed: " + (res.error || res.message));
      }
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  // Backend: Fetch SQLite Audit History
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

  // Client-side Export JSON
  const handleExportJson = () => {
    const payload = {
      reportId,
      exportedAt: new Date().toISOString(),
      instrument,
      conditions,
      readings,
      computation,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${reportId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Exported dataset as JSON");
  };

  // Client-side Export CSV
  const handleExportCsv = () => {
    const headers = [
      "Load_kg",
      "Reading_kg",
      "Direction",
      "Position",
      "Repeat",
      "Error_kg",
      "MPE_kg",
      "Passed",
    ];
    const rows = computation.pointResults.map((p) => [
      p.load,
      p.reading,
      p.direction,
      p.position || "center",
      p.repeatNumber || 1,
      p.error.toFixed(4),
      p.mpe.toFixed(4),
      p.passed ? "PASS" : "FAIL",
    ]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${reportId}_readings.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Exported readings ledger as CSV");
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] font-sans flex flex-col antialiased selection:bg-blue-100 selection:text-blue-900">
      {/* Toast Alert Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center space-x-2 bg-[#0F172A] text-white text-xs px-4 py-2.5 rounded-lg shadow-lg border border-slate-700 animate-in slide-in-from-bottom-2 no-print">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Global Navigation & Enterprise Header */}
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
        onOpenAttachments={() => setIsAttachmentModalOpen(true)}
      />

      {/* Real Role Switcher & User Session Header */}
      <AuthRoleSwitcher
        currentUser={currentUser}
        onUserChange={setCurrentUser}
        onOpenReviewerQueue={() => setIsReviewerModalOpen(true)}
        onOpenOwnerPortal={() => setIsOwnerModalOpen(true)}
        onNotification={showToast}
      />

      {/* Live Backend Telemetry Strip */}
      {backendOnline && dashboardStats && (
        <div className="bg-white border-b border-[#E2E8F0] px-4 sm:px-6 lg:px-8 py-2 text-xs flex items-center justify-between no-print">
          <div className="flex items-center space-x-4">
            <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] flex items-center space-x-1">
              <Activity className="w-3 h-3 text-emerald-600" />
              <span>Live Laboratory Telemetry:</span>
            </span>
            <span className="text-slate-700">
              Fleet:{" "}
              <strong className="font-mono text-slate-900">
                {dashboardStats.total_instruments || 0}
              </strong>{" "}
              scales
            </span>
            <span>·</span>
            <span className="text-slate-700">
              Evaluations:{" "}
              <strong className="font-mono text-slate-900">
                {dashboardStats.total_evaluations || 0}
              </strong>
            </span>
            <span>·</span>
            <span className="text-slate-700">
              Statutory Pass Rate:{" "}
              <strong className="font-mono text-emerald-700 font-semibold">
                {dashboardStats.pass_rate || 100}%
              </strong>
            </span>
            <span>·</span>
            <span className="text-slate-700">
              Expiring &lt;30d:{" "}
              <strong className="font-mono text-amber-700 font-semibold">
                {dashboardStats.expiring_soon_count || 0}
              </strong>
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsReviewerModalOpen(true)}
              className="text-[11px] text-blue-600 hover:text-blue-800 font-medium hover:underline flex items-center space-x-1"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Reviewer Queue</span>
            </button>
            <span>·</span>
            <button
              onClick={() => setIsOwnerModalOpen(true)}
              className="text-[11px] text-emerald-600 hover:text-emerald-800 font-medium hover:underline flex items-center space-x-1"
            >
              <Building className="w-3.5 h-3.5" />
              <span>Owner Fleet</span>
            </button>
            <span>·</span>
            <button
              onClick={() => setIsAttachmentModalOpen(true)}
              className="text-[11px] text-slate-600 hover:text-slate-800 font-medium hover:underline flex items-center space-x-1"
            >
              <Paperclip className="w-3.5 h-3.5" />
              <span>Evidence Attachments</span>
            </button>
          </div>
        </div>
      )}

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

      {/* Reviewer Queue Workflow Modal */}
      <ReviewerQueueModal
        isOpen={isReviewerModalOpen}
        onClose={() => setIsReviewerModalOpen(false)}
        onNotification={showToast}
      />

      {/* Owner Fleet Portal Modal */}
      <OwnerPortalModal
        isOpen={isOwnerModalOpen}
        onClose={() => setIsOwnerModalOpen(false)}
        ownerName={currentUser?.full_name || "Essae Digitronics"}
        onNotification={showToast}
      />

      {/* Attachment Upload & Download Modal */}
      <AttachmentUploadModal
        isOpen={isAttachmentModalOpen}
        onClose={() => setIsAttachmentModalOpen(false)}
        evaluationId="eval_seed_001"
        onNotification={showToast}
      />

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
