import React from "react";
import { AuditHistoryRecord } from "../types/metrology";
import {
  X,
  Database,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  User,
  Scale,
} from "lucide-react";

interface AuditHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  records: AuditHistoryRecord[];
  isLoading: boolean;
  onRefresh: () => void;
  onSelectEvaluation?: (evalId: string) => void;
}

export const AuditHistoryModal: React.FC<AuditHistoryModalProps> = ({
  isOpen,
  onClose,
  records,
  isLoading,
  onRefresh,
  onSelectEvaluation,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in no-print">
      <div className="bg-white rounded-lg shadow-xl border border-[#E2E8F0] max-w-4xl w-full max-h-[85vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-[#E2E8F0] flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#0F172A]">
                SQLite Statutory Audit Trail (nawi_audit.db)
              </h3>
              <p className="text-xs text-[#64748B]">
                Immutable historical test logs stored in the local metrology
                database
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onRefresh}
              className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded hover:bg-slate-50 transition-colors"
            >
              Refresh Logs
            </button>
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-700 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body / Table */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-500">
              Fetching audit records from SQLite database...
            </div>
          ) : records.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <Database className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs text-slate-600 font-medium">
                No audit records found in nawi_audit.db yet.
              </p>
              <p className="text-[11px] text-slate-400">
                Click "Save to SQLite Audit DB" on any test report to record an
                immutable entry.
              </p>
            </div>
          ) : (
            <div className="border border-[#E2E8F0] rounded overflow-hidden">
              <table className="w-full text-left text-xs border-collapse font-sans">
                <thead className="bg-slate-50 border-b border-[#E2E8F0] text-slate-600 font-medium">
                  <tr>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Report ID</th>
                    <th className="py-2.5 px-3">Instrument Model / Serial</th>
                    <th className="py-2.5 px-3">Class</th>
                    <th className="py-2.5 px-3">Score</th>
                    <th className="py-2.5 px-3">Risk Level</th>
                    <th className="py-2.5 px-3">Verdict</th>
                    <th className="py-2.5 px-3">Inspector</th>
                    {onSelectEvaluation && (
                      <th className="py-2.5 px-3 text-right">Action</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0] text-slate-800">
                  {records.map((r, i) => (
                    <tr
                      key={i}
                      className="hover:bg-slate-50 font-mono text-[11px]"
                    >
                      <td className="py-2.5 px-3 text-slate-500">
                        {r.created_at
                          ? r.created_at.slice(0, 19).replace("T", " ")
                          : "—"}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-900 truncate max-w-[140px]">
                        {r.report_id}
                      </td>
                      <td className="py-2.5 px-3 font-sans">
                        <div className="font-medium text-slate-900">
                          {r.instrument_model}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {r.instrument_serial}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] border border-blue-200">
                          Class {r.class}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-slate-900">
                        {r.compliance_score
                          ? Number(r.compliance_score).toFixed(1)
                          : 0}
                        %
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                            r.risk_level === "LOW"
                              ? "bg-emerald-50 text-emerald-800"
                              : r.risk_level === "MEDIUM"
                                ? "bg-amber-50 text-amber-800"
                                : "bg-red-50 text-red-800"
                          }`}
                        >
                          {r.risk_level}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-sans">
                        {r.conformity === 1 ? (
                          <span className="inline-flex items-center text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            PASS
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-[10px] font-bold text-red-700 bg-red-50 px-1.5 py-0.5 rounded border border-red-200">
                            FAIL
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-slate-600 truncate max-w-[120px]">
                        {r.inspector_name || "—"}
                      </td>
                      {onSelectEvaluation && (
                        <td className="py-2.5 px-3 text-right font-sans">
                          <div className="flex items-center justify-end space-x-1.5">
                            {r.pdf_url && (
                              <a
                                href={r.pdf_url}
                                target="_blank"
                                rel="noreferrer"
                                className="px-2 py-0.5 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-300 rounded hover:bg-emerald-100 transition-colors"
                                title="Download Stamped Final PDF"
                              >
                                PDF
                              </a>
                            )}
                            <button
                              onClick={() => onSelectEvaluation(r.report_id)}
                              className="px-2 py-0.5 text-[11px] font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                            >
                              Open
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-slate-50 border-t border-[#E2E8F0] flex items-center justify-between text-xs text-slate-500">
          <span>Total Logged Audits: {records.length}</span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 bg-slate-800 text-white rounded hover:bg-slate-700 font-medium text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
