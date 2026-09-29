import React, { useState } from "react";
import { AuditHistoryRecord } from "../types/metrology";
import {
  X,
  Database,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  User,
  Scale,
  Shield,
  Activity,
  Clock,
  Filter,
} from "lucide-react";

export interface SystemAuditLogEntry {
  id: number;
  timestamp: string;
  user_id: string;
  user_role?: string;
  user_name?: string;
  username?: string;
  organization?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: Record<string, any>;
  ip_address?: string;
}

interface AuditHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  records: AuditHistoryRecord[];
  auditLogs?: SystemAuditLogEntry[];
  isLoading: boolean;
  onRefresh: () => void;
  onSelectEvaluation?: (evalId: string) => void;
}

export const AuditHistoryModal: React.FC<AuditHistoryModalProps> = ({
  isOpen,
  onClose,
  records,
  auditLogs = [],
  isLoading,
  onRefresh,
  onSelectEvaluation,
}) => {
  const [activeTab, setActiveTab] = useState<"logs" | "records">("logs");
  const [filterAction, setFilterAction] = useState<string>("ALL");

  if (!isOpen) return null;

  const getActionBadgeClass = (action: string) => {
    switch (action) {
      case "LOGIN":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "LOGOUT":
        return "bg-slate-100 text-slate-700 border-slate-200";
      case "CREATE_INSTRUMENT":
      case "UPDATE_INSTRUMENT":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "CREATE_EVALUATION":
      case "UPDATE_EVALUATION":
        return "bg-indigo-50 text-indigo-700 border-indigo-200";
      case "SUBMIT_TEST_READINGS":
      case "CALCULATE":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "SUBMIT_FOR_REVIEW":
      case "RESUBMIT_FOR_REVIEW":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "REVIEW_INSPECT":
        return "bg-yellow-50 text-yellow-800 border-yellow-200";
      case "REVIEW_APPROVE":
        return "bg-green-100 text-green-800 border-green-300 font-bold";
      case "REVIEW_RETURN":
      case "REVIEW_REJECT":
        return "bg-rose-50 text-rose-700 border-rose-200 font-semibold";
      case "UPLOAD_ATTACHMENT":
        return "bg-cyan-50 text-cyan-700 border-cyan-200";
      case "GENERATE_REPORT":
        return "bg-teal-50 text-teal-800 border-teal-200 font-semibold";
      case "DELETE_INSTRUMENT":
      case "DELETE_EVALUATION":
      case "DELETE_ATTACHMENT":
        return "bg-red-50 text-red-700 border-red-200";
      default:
        return "bg-slate-100 text-slate-800 border-slate-200";
    }
  };

  const getRoleBadgeClass = (role?: string) => {
    switch ((role || "").toUpperCase()) {
      case "ADMIN":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "REVIEWER":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "INSPECTOR":
      case "TECHNICIAN":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "OWNER":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const filteredLogs = auditLogs.filter((log) => {
    if (filterAction === "ALL") return true;
    if (filterAction === "AUTH")
      return log.action === "LOGIN" || log.action === "LOGOUT";
    if (filterAction === "EVAL")
      return (
        log.action.includes("EVALUATION") ||
        log.action.includes("READING") ||
        log.action === "CALCULATE"
      );
    if (filterAction === "REVIEW")
      return log.action.includes("REVIEW") || log.action.includes("SUBMIT");
    if (filterAction === "REPORT")
      return (
        log.action === "GENERATE_REPORT" || log.action.includes("ATTACHMENT")
      );
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in no-print">
      <div className="bg-white rounded-lg shadow-xl border border-[#E2E8F0] max-w-5xl w-full max-h-[88vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-[#E2E8F0] flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#0F172A]">
                Legal Metrology Statutory Audit Trail (nawi_audit.db)
              </h3>
              <p className="text-xs text-[#64748B]">
                Immutable, cryptographically verifiable system audit history
                under OIML R-76 & Legal Metrology Act
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onRefresh}
              className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded hover:bg-slate-50 transition-colors"
            >
              Refresh
            </button>
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-700 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Switcher & Filter Bar */}
        <div className="px-4 sm:px-5 pt-3 border-b border-[#E2E8F0] bg-white flex flex-wrap items-center justify-between gap-2">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab("logs")}
              className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition-colors flex items-center space-x-1.5 ${
                activeTab === "logs"
                  ? "border-blue-600 text-blue-600 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>System Activity Audit Trail</span>
              <span className="ml-1.5 px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded-full text-[10px]">
                {auditLogs.length}
              </span>
            </button>
            <button
              onClick={() => setActiveTab("records")}
              className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition-colors flex items-center space-x-1.5 ${
                activeTab === "records"
                  ? "border-blue-600 text-blue-600 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Scale className="w-3.5 h-3.5" />
              <span>Statutory Verification Records</span>
              <span className="ml-1.5 px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded-full text-[10px]">
                {records.length}
              </span>
            </button>
          </div>

          {activeTab === "logs" && (
            <div className="flex items-center space-x-1 pb-2">
              <Filter className="w-3 h-3 text-slate-400 mr-1" />
              {["ALL", "AUTH", "EVAL", "REVIEW", "REPORT"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setFilterAction(cat)}
                  className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                    filterAction === cat
                      ? "bg-slate-800 text-white font-semibold"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Modal Body / Table */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-500">
              Fetching statutory audit records from SQLite database...
            </div>
          ) : activeTab === "logs" ? (
            // TAB 1: System Activity Audit Trail
            filteredLogs.length === 0 ? (
              <div className="py-12 text-center space-y-2">
                <Activity className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-xs text-slate-600 font-medium">
                  No activity log entries found.
                </p>
                <p className="text-[11px] text-slate-400">
                  System events (login, evaluation creation, readings, reviews,
                  reports) are recorded here automatically.
                </p>
              </div>
            ) : (
              <div className="border border-[#E2E8F0] rounded overflow-hidden">
                <table className="w-full text-left text-xs border-collapse font-sans">
                  <thead className="bg-slate-50 border-b border-[#E2E8F0] text-slate-600 font-medium">
                    <tr>
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Actor / User</th>
                      <th className="py-2.5 px-3">Role</th>
                      <th className="py-2.5 px-3">Action</th>
                      <th className="py-2.5 px-3">Entity</th>
                      <th className="py-2.5 px-3">Statutory Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0] text-slate-800">
                    {filteredLogs.map((log) => {
                      const details = log.details || {};
                      return (
                        <tr
                          key={log.id}
                          className="hover:bg-slate-50 font-mono text-[11px]"
                        >
                          <td className="py-2 px-3 text-slate-500 whitespace-nowrap">
                            {log.timestamp
                              ? log.timestamp.slice(0, 19).replace("T", " ")
                              : "—"}
                          </td>
                          <td className="py-2 px-3 font-sans">
                            <div className="font-semibold text-slate-900 leading-tight">
                              {log.user_name || log.username || log.user_id}
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono">
                              {log.user_id}
                            </div>
                          </td>
                          <td className="py-2 px-3 font-sans">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] border font-medium uppercase ${getRoleBadgeClass(
                                log.user_role,
                              )}`}
                            >
                              {log.user_role || "SYSTEM"}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-sans">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] border font-semibold inline-block whitespace-nowrap ${getActionBadgeClass(
                                log.action,
                              )}`}
                            >
                              {log.action}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-sans">
                            <div className="text-[10px] font-semibold text-slate-700">
                              {log.entity_type}
                            </div>
                            <div
                              className="text-[10px] text-slate-400 font-mono truncate max-w-[120px]"
                              title={log.entity_id}
                            >
                              {log.entity_id}
                            </div>
                          </td>
                          <td className="py-2 px-3 font-sans text-[11px] text-slate-700">
                            {details.status && (
                              <span className="inline-block mr-2 text-[10px] bg-slate-100 text-slate-700 px-1 rounded">
                                Status: <strong>{details.status}</strong>
                              </span>
                            )}
                            {details.certificate_number && (
                              <span className="inline-block mr-2 text-[10px] bg-emerald-50 text-emerald-800 px-1 rounded border border-emerald-200">
                                Cert:{" "}
                                <strong>{details.certificate_number}</strong>
                              </span>
                            )}
                            {details.serial_number && (
                              <span className="inline-block mr-2 text-[10px] text-slate-600">
                                SN: <strong>{details.serial_number}</strong>
                              </span>
                            )}
                            {details.readings_count !== undefined && (
                              <span className="inline-block mr-2 text-[10px] text-slate-600">
                                Readings:{" "}
                                <strong>{details.readings_count}</strong>
                              </span>
                            )}
                            {details.compliance_score !== undefined && (
                              <span className="inline-block mr-2 text-[10px] text-blue-700">
                                Score:{" "}
                                <strong>
                                  {Number(details.compliance_score).toFixed(1)}%
                                </strong>
                              </span>
                            )}
                            {details.filename && (
                              <span className="inline-block mr-2 text-[10px] text-slate-600 font-mono">
                                File: {details.filename}
                              </span>
                            )}
                            {details.comments && (
                              <span
                                className="inline-block text-[10px] text-slate-500 italic max-w-xs truncate"
                                title={details.comments}
                              >
                                "{details.comments}"
                              </span>
                            )}
                            {!details.status &&
                              !details.certificate_number &&
                              !details.serial_number &&
                              !details.readings_count &&
                              !details.filename && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  {Object.keys(details).length > 0
                                    ? JSON.stringify(details)
                                    : "—"}
                                </span>
                              )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          ) : // TAB 2: Statutory Verification Records (Preserved 100%)
          records.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <Database className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs text-slate-600 font-medium">
                No statutory evaluation reports found in nawi_audit.db yet.
              </p>
              <p className="text-[11px] text-slate-400">
                Save and approve metrological evaluations to generate official
                statutory records.
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
          <span>
            {activeTab === "logs"
              ? `Total System Activity Logs: ${filteredLogs.length}`
              : `Total Statutory Records: ${records.length}`}
          </span>
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
