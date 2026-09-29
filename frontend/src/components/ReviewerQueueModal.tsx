import React, { useState, useEffect } from "react";
import {
  X,
  CheckCircle,
  XCircle,
  FileText,
  AlertTriangle,
  Download,
  RefreshCw,
  ShieldCheck,
  RotateCcw,
  Eye,
} from "lucide-react";
import {
  fetchEvaluations,
  reviewEvaluation,
  generateEvaluationPdf,
} from "../utils/apiClient";

interface ReviewerQueueModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNotification: (msg: string) => void;
  onSelectEvaluation?: (evalId: string) => void;
}

export const ReviewerQueueModal: React.FC<ReviewerQueueModalProps> = ({
  isOpen,
  onClose,
  onNotification,
  onSelectEvaluation,
}) => {
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEval, setSelectedEval] = useState<any | null>(null);
  const [comments, setComments] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const data = await fetchEvaluations();
      // Prioritize SUBMITTED, then show all
      setEvaluations(data);
      if (data.length > 0 && !selectedEval) {
        setSelectedEval(data[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadQueue();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleReviewAction = async (verdict: "APPROVE" | "REJECT" | "RETURN" | "UNDER_REVIEW") => {
    if (!selectedEval) return;
    if ((verdict === "REJECT" || verdict === "RETURN") && !comments.trim()) {
      alert(
        "Please provide remarks explaining why the evaluation was returned/rejected for correction.",
      );
      return;
    }
    setActionLoading(true);
    try {
      const res = await reviewEvaluation(
        selectedEval.id,
        verdict,
        comments ||
          (verdict === "APPROVE"
            ? "Statutory OIML R-76 requirements verified and approved."
            : verdict === "UNDER_REVIEW"
              ? "Inspection initiated by Reviewer."
              : "Returned for correction."),
      );
      if (res.success) {
        onNotification(
          `Evaluation ${selectedEval.serial_number || selectedEval.id} status updated to ${res.status || verdict}`,
        );
        setComments("");
        await loadQueue();
        if (selectedEval) {
          setSelectedEval({ ...selectedEval, status: res.status || verdict });
        }
      } else {
        alert(res.error || "Failed to review evaluation");
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadPdf = async (evalId: string) => {
    setActionLoading(true);
    try {
      const res = await generateEvaluationPdf(evalId);
      if (res.success && (res.report_url || res.pdf_url)) {
        window.open(res.report_url || res.pdf_url, "_blank");
      } else {
        alert(res.error || "Could not generate official PDF");
      }
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#0F172A]">
                Reviewer Approval Queue & Workflow
              </h2>
              <p className="text-xs text-[#64748B]">
                OIML R-76 Statutory Verification & Stamping Portal
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadQueue}
              disabled={loading}
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
              title="Refresh Queue"
            >
              <RefreshCw
                className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
              />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content: Split List and Inspector Review Panel */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left List */}
          <div className="w-1/3 border-r border-[#E2E8F0] overflow-y-auto p-3 space-y-2 bg-slate-50/30">
            <div className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider px-2 py-1">
              Evaluations ({evaluations.length})
            </div>
            {evaluations.map((ev) => {
              const isSelected = selectedEval?.id === ev.id;
              const isSubmitted = ev.status === "SUBMITTED";
              const isApproved = ev.status === "APPROVED";
              return (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEval(ev)}
                  className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                    isSelected
                      ? "bg-blue-50/60 border-blue-500 shadow-sm"
                      : "bg-white border-[#E2E8F0] hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-semibold text-[#0F172A]">
                      {ev.serial_number}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-medium border ${
                        ev.status === "APPROVED"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : ev.status === "SUBMITTED"
                            ? "bg-amber-50 text-amber-700 border-amber-200 animate-pulse font-semibold"
                            : ev.status === "UNDER_REVIEW"
                              ? "bg-blue-50 text-blue-700 border-blue-200"
                              : ev.status === "RETURNED"
                                ? "bg-orange-50 text-orange-700 border-orange-200"
                                : ev.status === "REJECTED"
                                  ? "bg-rose-50 text-rose-700 border-rose-200"
                                  : "bg-slate-100 text-slate-700 border-slate-200"
                      }`}
                    >
                      {ev.status}
                    </span>
                  </div>
                  <div className="text-xs text-[#64748B] truncate">
                    {ev.model} • {ev.manufacturer}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-[#64748B]">
                    <span>
                      Score:{" "}
                      <strong className="text-slate-800">
                        {ev.compliance_score || 100}%
                      </strong>
                    </span>
                    <span>Inspector: {ev.inspector_name || "Rajesh"}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Details & Action Panel */}
          <div className="w-2/3 p-6 overflow-y-auto flex flex-col">
            {selectedEval ? (
              <div className="space-y-5 flex-1">
                <div className="flex items-center justify-between pb-4 border-b border-[#E2E8F0]">
                  <div>
                    <h3 className="text-lg font-bold text-[#0F172A]">
                      {selectedEval.model}
                    </h3>
                    <p className="text-xs font-mono text-[#64748B]">
                      Serial: {selectedEval.serial_number} | Class{" "}
                      {selectedEval.accuracy_class}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-medium text-[#64748B]">
                      OIML Verdict
                    </div>
                    <div
                      className={`text-base font-bold font-mono ${selectedEval.conformity ? "text-emerald-600" : "text-rose-600"}`}
                    >
                      {selectedEval.conformity
                        ? "PASSED (MPE Valid)"
                        : "FAILED (Exceeds MPE)"}
                    </div>
                  </div>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-slate-50 p-2.5 rounded border border-[#E2E8F0]">
                    <div className="text-[10px] text-[#64748B]">
                      Compliance Score
                    </div>
                    <div className="text-sm font-bold text-slate-900 font-mono">
                      {selectedEval.compliance_score}%
                    </div>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded border border-[#E2E8F0]">
                    <div className="text-[10px] text-[#64748B]">Risk Level</div>
                    <div className="text-sm font-bold text-slate-900">
                      {selectedEval.risk_level || "LOW"}
                    </div>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded border border-[#E2E8F0]">
                    <div className="text-[10px] text-[#64748B]">
                      Expanded Uncert. U
                    </div>
                    <div className="text-sm font-bold text-slate-900 font-mono">
                      {selectedEval.expanded_uncertainty || 0} kg
                    </div>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded border border-[#E2E8F0]">
                    <div className="text-[10px] text-[#64748B]">
                      Max Capacity
                    </div>
                    <div className="text-sm font-bold text-slate-900 font-mono">
                      {selectedEval.max_capacity} kg
                    </div>
                  </div>
                </div>

                {/* Verification Hash & Certificate */}
                <div className="p-3 bg-slate-50 rounded border border-[#E2E8F0] space-y-1">
                  <div className="text-[11px] font-semibold text-[#0F172A]">
                    Cryptographic Verification Digest:
                  </div>
                  <div className="font-mono text-xs text-blue-700 bg-white p-2 rounded border border-slate-200 break-all select-all">
                    {selectedEval.verification_hash || "OIML-R76-2026-HASH"}
                  </div>
                  {selectedEval.certificate_number && (
                    <div className="text-xs text-emerald-700 font-medium pt-1">
                      Certificate No:{" "}
                      <span className="font-mono font-bold">
                        {selectedEval.certificate_number}
                      </span>
                    </div>
                  )}
                </div>

                {/* Review Comments & Stamping Section */}
                <div className="space-y-2 pt-2">
                  <label className="block text-xs font-semibold text-[#0F172A]">
                    Reviewer Statutory Comments / Rejection Reason:
                  </label>
                  <textarea
                    rows={3}
                    value={comments}
                    onChange={(e) => setComments(e.target.value)}
                    placeholder="Enter verification comments or stamping endorsement details..."
                    className="w-full text-xs p-2.5 border border-[#E2E8F0] rounded-lg focus:outline-none focus:border-blue-600 font-sans"
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-4 border-t border-[#E2E8F0]">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleDownloadPdf(selectedEval.id)}
                      disabled={actionLoading}
                      className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 shadow-sm transition-colors"
                    >
                      <Download className="w-4 h-4 text-blue-600" />
                      <span>Generate Official PDF</span>
                    </button>
                    {onSelectEvaluation && (
                      <button
                        onClick={async () => {
                          if (selectedEval.status === "SUBMITTED") {
                            await handleReviewAction("UNDER_REVIEW");
                          }
                          onSelectEvaluation(selectedEval.id);
                        }}
                        className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 shadow-sm transition-colors"
                        title="Open evaluation readings & test records in Metrolab workspace"
                      >
                        <FileText className="w-4 h-4 text-blue-600" />
                        <span>Open in Workspace</span>
                      </button>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {selectedEval.status === "SUBMITTED" && (
                      <button
                        onClick={() => handleReviewAction("UNDER_REVIEW")}
                        disabled={actionLoading}
                        className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                        title="Mark evaluation as actively under statutory review"
                      >
                        <Eye className="w-4 h-4" />
                        <span>Inspect</span>
                      </button>
                    )}
                    <button
                      onClick={() => handleReviewAction("RETURN")}
                      disabled={actionLoading}
                      className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-amber-800 bg-amber-50 border border-amber-300 rounded hover:bg-amber-100 transition-colors"
                      title="Return evaluation back to technician for corrections"
                    >
                      <RotateCcw className="w-4 h-4 text-amber-600" />
                      <span>Return for Correction</span>
                    </button>
                    <button
                      onClick={() => handleReviewAction("REJECT")}
                      disabled={actionLoading}
                      className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200 rounded hover:bg-rose-100 transition-colors"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Reject</span>
                    </button>
                    <button
                      onClick={() => handleReviewAction("APPROVE")}
                      disabled={actionLoading}
                      className="flex items-center space-x-1.5 px-4 py-2 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded shadow-sm transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                      <span>Approve & Stamp Certificate</span>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-[#64748B]">
                Select an evaluation from the list to review.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
