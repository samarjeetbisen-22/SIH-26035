import React, { useState, useEffect } from 'react';
import { X, Building2, Calendar, FileText, Download, CheckCircle, AlertTriangle, RefreshCw, Plus } from 'lucide-react';
import { fetchInstruments, fetchEvaluations, generateEvaluationPdf } from '../utils/apiClient';

interface OwnerPortalModalProps {
  isOpen: boolean;
  onClose: () => void;
  ownerName: string;
  onNotification: (msg: string) => void;
}

export const OwnerPortalModal: React.FC<OwnerPortalModalProps> = ({ isOpen, onClose, ownerName, onNotification }) => {
  const [instruments, setInstruments] = useState<any[]>([]);
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const loadOwnerData = async () => {
    setLoading(true);
    try {
      const [instData, evalData] = await Promise.all([
        fetchInstruments(),
        fetchEvaluations()
      ]);
      setInstruments(instData);
      setEvaluations(evalData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadOwnerData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const calculateDaysRemaining = (dueDateStr?: string) => {
    if (!dueDateStr) return null;
    const due = new Date(dueDateStr);
    const now = new Date();
    const diffTime = due.getTime() - now.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const handleDownloadPdf = async (instId: string) => {
    // Find matching evaluation
    const matchingEval = evaluations.find(e => e.instrument_id === instId);
    if (!matchingEval) {
      alert('No formal evaluation report available for this scale yet.');
      return;
    }
    setActionLoading(true);
    try {
      const res = await generateEvaluationPdf(matchingEval.id);
      if (res.success && (res.report_url || res.pdf_url)) {
        window.open(res.report_url || res.pdf_url, '_blank');
      } else {
        alert(res.error || 'Could not retrieve verification certificate');
      }
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#0F172A]">Owner Fleet Portal & Stamping Status</h2>
              <p className="text-xs text-[#64748B]">Managing legal compliance for: <strong className="text-slate-800">{ownerName}</strong></p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadOwnerData}
              disabled={loading}
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Table */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">
              Registered Fleet Instruments ({instruments.length})
            </span>
            <span className="text-xs text-blue-600 bg-blue-50 px-2.5 py-1 rounded border border-blue-200">
              Isolated Owner Access Only
            </span>
          </div>

          <div className="border border-[#E2E8F0] rounded-lg overflow-hidden shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[#64748B] uppercase tracking-wider font-mono text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">Serial & Model</th>
                  <th className="py-2.5 px-4">Class & Cap</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Validity Countdown</th>
                  <th className="py-2.5 px-4 text-right">Certificate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {instruments.map((inst) => {
                  const daysLeft = calculateDaysRemaining(inst.next_verification_due);
                  const isVerified = inst.status === 'VERIFIED';
                  return (
                    <tr key={inst.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-slate-900">
                        <div>{inst.serial_number}</div>
                        <div className="text-[11px] font-sans text-slate-500 font-normal">{inst.model}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 font-mono">
                        Class {inst.accuracy_class} • {inst.max_capacity} kg
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${
                            isVerified
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}
                        >
                          {isVerified ? <CheckCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                          <span>{inst.status}</span>
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-700 font-mono">
                        {daysLeft !== null ? (
                          <span className={daysLeft > 30 ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                            {daysLeft > 0 ? `${daysLeft} days remaining` : 'EXPIRED - Re-test Due'}
                          </span>
                        ) : (
                          <span className="text-slate-400">Not verified yet</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleDownloadPdf(inst.id)}
                          disabled={actionLoading}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>PDF Certificate</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#E2E8F0] bg-slate-50 text-right">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-100 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
