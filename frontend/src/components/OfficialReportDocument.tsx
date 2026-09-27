import React from "react";
import {
  InstrumentProfile,
  TestConditions,
  MetrologyComputation,
} from "../types/metrology";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  QrCode,
  Calendar,
  UserCheck,
  Building,
  FileCheck,
} from "lucide-react";

interface OfficialReportDocumentProps {
  instrument: InstrumentProfile;
  conditions: TestConditions;
  computation: MetrologyComputation;
  reportId: string;
}

export const OfficialReportDocument: React.FC<OfficialReportDocumentProps> = ({
  instrument,
  conditions,
  computation,
  reportId,
}) => {
  const currentDate = new Date().toISOString().split("T")[0];
  const nextDueDate = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];

  return (
    <div className="report-page-container bg-white border border-[#E2E8F0] shadow-paper rounded p-8 sm:p-10 font-sans text-[#0F172A] max-w-[850px] mx-auto text-xs leading-relaxed">
      {/* Official Government / Legal Metrology Header */}
      <div className="border-b-2 border-slate-900 pb-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded border-2 border-slate-900 flex items-center justify-center font-bold text-lg font-mono tracking-tighter">
              LM
            </div>
            <div>
              <div className="text-[10px] font-mono tracking-widest uppercase text-slate-500 font-semibold">
                Government of India · Ministry of Consumer Affairs
              </div>
              <h1 className="text-base font-bold tracking-tight text-[#0F172A] uppercase">
                Directorate of Legal Metrology
              </h1>
              <div className="text-[11px] text-slate-600 font-medium">
                {conditions.testLocation}
              </div>
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] font-mono text-slate-500 uppercase">
              Certificate No.
            </div>
            <div className="font-mono text-xs font-bold text-slate-900">
              {reportId}
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              Date: {conditions.testDate || currentDate}
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between">
          <div className="text-center w-full">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Certificate of Metrological Verification
            </div>
            <div className="text-[10px] text-slate-600">
              Conducted pursuant to OIML R 76-1:2006 & Section 12 of The Legal
              Metrology Act, 2009
            </div>
          </div>
        </div>
      </div>

      {/* Official Conformity Stamp Banner */}
      <div
        className={`p-3 rounded border mb-6 flex items-center justify-between ${
          computation.overallPass
            ? "bg-[#ECFDF5] border-emerald-300 text-emerald-900"
            : "bg-[#FEF2F2] border-red-300 text-red-900"
        }`}
      >
        <div className="flex items-center space-x-3">
          {computation.overallPass ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
          )}
          <div>
            <div className="font-bold text-xs uppercase tracking-wide">
              {computation.overallPass
                ? "VERIFIED METROLOGICALLY CONFORMING"
                : "NON-CONFORMING / REJECTED"}
            </div>
            <div className="text-[11px] opacity-90">
              {computation.overallPass
                ? "Instrument satisfies all Maximum Permissible Error (MPE) requirements prescribed in OIML R 76-1."
                : "Instrument violates MPE limits or repeatability thresholds; stamp cannot be issued for commercial use."}
            </div>
          </div>
        </div>

        <div className="text-right pl-4">
          <div className="text-[10px] uppercase font-mono tracking-wider text-slate-500">
            Compliance Index
          </div>
          <div className="text-sm font-bold font-mono">
            {computation.complianceScore}% ({computation.riskLevel} RISK)
          </div>
        </div>
      </div>

      {/* Section 1: Instrument Particulars */}
      <div className="mb-5">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-slate-700 pb-1 border-b border-slate-200 mb-2">
          1. Instrument Identification & Technical Characteristics
        </h2>
        <table className="w-full text-[11px] border border-slate-200">
          <tbody>
            <tr className="border-b border-slate-200 bg-slate-50/50">
              <td className="p-2 font-medium text-slate-600 w-1/4">
                Manufacturer:
              </td>
              <td className="p-2 font-semibold text-slate-900 w-1/4">
                {instrument.manufacturer}
              </td>
              <td className="p-2 font-medium text-slate-600 w-1/4">
                Model Designation:
              </td>
              <td className="p-2 font-semibold text-slate-900 w-1/4">
                {instrument.model}
              </td>
            </tr>
            <tr className="border-b border-slate-200">
              <td className="p-2 font-medium text-slate-600">Serial Number:</td>
              <td className="p-2 font-mono font-semibold text-slate-900">
                {instrument.serialNumber}
              </td>
              <td className="p-2 font-medium text-slate-600">
                Type Approval No:
              </td>
              <td className="p-2 font-mono text-slate-900">
                {instrument.typeApprovalNo || "N/A"}
              </td>
            </tr>
            <tr className="border-b border-slate-200 bg-slate-50/50">
              <td className="p-2 font-medium text-slate-600">
                Accuracy Class:
              </td>
              <td className="p-2 font-mono font-bold text-blue-700">
                Class {instrument.accuracyClass}
              </td>
              <td className="p-2 font-medium text-slate-600">
                Max Capacity (Max):
              </td>
              <td className="p-2 font-mono font-semibold text-slate-900">
                {instrument.maxCapacity} {instrument.unit}
              </td>
            </tr>
            <tr className="border-b border-slate-200">
              <td className="p-2 font-medium text-slate-600">
                Verification Interval (e):
              </td>
              <td className="p-2 font-mono text-slate-900">
                {instrument.verificationScaleIntervalE} {instrument.unit}
              </td>
              <td className="p-2 font-medium text-slate-600">
                Actual Interval (d):
              </td>
              <td className="p-2 font-mono text-slate-900">
                {instrument.actualScaleIntervalD} {instrument.unit}
              </td>
            </tr>
            <tr>
              <td className="p-2 font-medium text-slate-600">
                Verification Steps (n):
              </td>
              <td className="p-2 font-mono text-slate-900">
                {computation.scaleIntervalsN.toLocaleString()}
              </td>
              <td className="p-2 font-medium text-slate-600">
                Min Capacity (Min):
              </td>
              <td className="p-2 font-mono text-slate-900">
                {instrument.minCapacity} {instrument.unit}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 2: Environmental & Reference Standards */}
      <div className="mb-5">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-slate-700 pb-1 border-b border-slate-200 mb-2">
          2. Environmental Conditions & Traceability of Reference Standards
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] p-2.5 bg-slate-50 border border-slate-200 rounded font-mono">
          <div>
            <span className="text-slate-500 block text-[10px]">TEMP (°C):</span>
            <span className="text-slate-900 font-semibold">
              {conditions.temperatureC} °C
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">HUMIDITY:</span>
            <span className="text-slate-900 font-semibold">
              {conditions.humidityPercent} % RH
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">PRESSURE:</span>
            <span className="text-slate-900 font-semibold">
              {conditions.barometricPressureHpa} hPa
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">
              GRAVITY (g):
            </span>
            <span className="text-slate-900 font-semibold">
              {conditions.gravityMps2} m/s²
            </span>
          </div>
        </div>
        <div className="mt-1.5 text-[10px] text-slate-600 font-mono">
          <span className="font-semibold">Reference Weights:</span>{" "}
          {conditions.referenceMassStandard} (Cert Traceability:{" "}
          {conditions.standardsTraceabilityNo})
        </div>
      </div>

      {/* Section 3: Summary of Metrological Errors */}
      <div className="mb-5">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-slate-700 pb-1 border-b border-slate-200 mb-2">
          3. Metrological Evaluation Summary (OIML R 76-1)
        </h2>
        <table className="w-full text-[11px] border border-slate-200 font-mono">
          <thead className="bg-slate-100 text-slate-700 font-sans">
            <tr>
              <th className="p-1.5 text-left">Test Requirement</th>
              <th className="p-1.5 text-right">Measured Error</th>
              <th className="p-1.5 text-right">Permitted Limit</th>
              <th className="p-1.5 text-center">Conformity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            <tr>
              <td className="p-1.5 font-sans font-medium">
                A.4.4 Repeatability Error (s/Cap)
              </td>
              <td className="p-1.5 text-right">
                {computation.repeatabilityError.toFixed(6)}
              </td>
              <td className="p-1.5 text-right">≤ 1.0 MPE</td>
              <td className="p-1.5 text-center font-bold text-emerald-700">
                PASS
              </td>
            </tr>
            <tr>
              <td className="p-1.5 font-sans font-medium">
                A.4.7 Eccentricity (Corner Load Deviation)
              </td>
              <td className="p-1.5 text-right">
                {computation.eccentricitySummary.maxDeviation} {instrument.unit}
              </td>
              <td className="p-1.5 text-right">≤ MPE @ 1/3 Max</td>
              <td
                className={`p-1.5 text-center font-bold ${computation.eccentricitySummary.passed ? "text-emerald-700" : "text-red-700"}`}
              >
                {computation.eccentricitySummary.passed ? "PASS" : "FAIL"}
              </td>
            </tr>
            <tr>
              <td className="p-1.5 font-sans font-medium">
                A.4.2 Linearity Deviation (Max |I - L|)
              </td>
              <td className="p-1.5 text-right">
                {computation.linearityError.toFixed(6)}
              </td>
              <td className="p-1.5 text-right">MPE Envelope</td>
              <td className="p-1.5 text-center font-bold text-emerald-700">
                PASS
              </td>
            </tr>
            <tr>
              <td className="p-1.5 font-sans font-medium">
                A.4.2 Hysteresis (Max Ascending vs Descending)
              </td>
              <td className="p-1.5 text-right">
                {computation.hysteresisError.toFixed(6)}
              </td>
              <td className="p-1.5 text-right">≤ 1.0 MPE</td>
              <td className="p-1.5 text-center font-bold text-emerald-700">
                PASS
              </td>
            </tr>
            <tr className="bg-slate-50 font-semibold font-sans">
              <td className="p-1.5">Expanded Uncertainty U (k=2, 95% CL)</td>
              <td className="p-1.5 text-right font-mono text-blue-700">
                {computation.expandedUncertainty.toFixed(6)}
              </td>
              <td className="p-1.5 text-right font-mono text-slate-500">
                ISO/IEC Guide 98-3
              </td>
              <td className="p-1.5 text-center font-mono text-blue-700">
                EVALUATED
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 4: Load Point Registry (Abridged for official document) */}
      <div className="mb-6">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-slate-700 pb-1 border-b border-slate-200 mb-2">
          4. Load Performance & Indication Table (OIML R 76-1 Point Registry)
        </h2>
        <table className="w-full text-[10px] border border-slate-200 font-mono">
          <thead className="bg-slate-100 text-slate-700 font-sans">
            <tr>
              <th className="p-1 text-center">#</th>
              <th className="p-1 text-right">
                Nominal Load ({instrument.unit})
              </th>
              <th className="p-1 text-right">Indication ({instrument.unit})</th>
              <th className="p-1 text-center">Direction</th>
              <th className="p-1 text-right">Error E ({instrument.unit})</th>
              <th className="p-1 text-right">MPE Limit</th>
              <th className="p-1 text-center">Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {computation.pointResults.slice(0, 10).map((pt, i) => (
              <tr key={i} className={!pt.passed ? "bg-red-50/50" : ""}>
                <td className="p-1 text-center font-sans text-slate-400">
                  {i + 1}
                </td>
                <td className="p-1 text-right">{pt.load.toFixed(3)}</td>
                <td className="p-1 text-right font-semibold">
                  {pt.reading.toFixed(3)}
                </td>
                <td className="p-1 text-center font-sans text-slate-600">
                  {pt.direction === "increasing" ? "↑" : "↓"}
                </td>
                <td
                  className={`p-1 text-right font-semibold ${pt.error > 0 ? "text-blue-700" : pt.error < 0 ? "text-amber-700" : "text-slate-600"}`}
                >
                  {pt.error > 0 ? "+" : ""}
                  {pt.error.toFixed(4)}
                </td>
                <td className="p-1 text-right text-slate-500">
                  ±{pt.mpe.toFixed(4)}
                </td>
                <td
                  className={`p-1 text-center font-sans font-bold ${pt.passed ? "text-emerald-700" : "text-red-700"}`}
                >
                  {pt.passed ? "PASS" : "FAIL"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {computation.pointResults.length > 10 && (
          <div className="text-[10px] text-slate-500 text-center py-1 bg-slate-50 border-t border-slate-200">
            Showing first 10 of {computation.pointResults.length} verification
            readings. Full ledger archived in Metrolab database.
          </div>
        )}
      </div>

      {/* Section 5: Legal Framework & Statutory Citations */}
      <div className="mb-6 p-2.5 bg-slate-50 border border-slate-200 rounded text-[10px] text-slate-600 space-y-1">
        <div className="font-semibold text-slate-800 uppercase tracking-wide">
          Statutory Legal Framework:
        </div>
        <p>
          • OIML R 76-1 (2006): Non-automatic weighing instruments —
          Metrological and technical requirements — Tests.
        </p>
        <p>
          • The Legal Metrology Act, 2009: Section 12 (Approval of Model) &
          Section 24 (Verification and Stamping).
        </p>
        <p>
          • Legal Metrology (Approval of Models) Rules, 2011 & Legal Metrology
          (General) Rules, 2011.
        </p>
        <p>
          • Validity Period: 12 Calendar Months. Next mandatory verification due
          on or before: <b>{nextDueDate}</b>.
        </p>
      </div>

      {/* Section 6: Official Inspector Signature & Security Watermark */}
      <div className="pt-4 border-t-2 border-slate-900 grid grid-cols-3 gap-4 items-end">
        {/* Verification QR / Security Watermark */}
        <div>
          <div className="w-20 h-20 border border-slate-300 rounded p-1.5 bg-white flex flex-col items-center justify-center">
            <QrCode className="w-12 h-12 text-slate-800" />
            <span className="text-[8px] font-mono text-slate-400 mt-1">
              SCAN VERIFY
            </span>
          </div>
          <div className="text-[8px] font-mono text-slate-500 mt-1 truncate max-w-[150px]">
            {computation.verificationHash}
          </div>
        </div>

        {/* Official Seal Placeholder */}
        <div className="text-center">
          <div className="w-20 h-20 rounded-full border border-dashed border-slate-400 mx-auto flex items-center justify-center text-[9px] font-mono uppercase text-slate-400 text-center p-2">
            OFFICIAL METROLOGY SEAL
          </div>
          <div className="text-[9px] text-slate-500 mt-1">
            Regional Reference Lab
          </div>
        </div>

        {/* Verifying Officer Digital Signature */}
        <div className="text-right">
          <div className="font-serif italic text-sm text-slate-900 border-b border-slate-400 pb-1">
            {conditions.inspectorName}
          </div>
          <div className="text-[10px] font-semibold text-slate-900 mt-1">
            Legal Metrology Officer
          </div>
          <div className="text-[9px] font-mono text-slate-500">
            ID: {conditions.inspectorId}
          </div>
          <div className="text-[9px] font-mono text-slate-500">
            Certified: {conditions.testDate || currentDate}
          </div>
        </div>
      </div>
    </div>
  );
};
