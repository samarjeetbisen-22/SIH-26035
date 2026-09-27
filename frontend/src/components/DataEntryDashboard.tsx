import React, { useState } from "react";
import {
  InstrumentProfile,
  ReadingItem,
  PlatformPosition,
  LoadDirection,
  MetrologyComputation,
} from "../types/metrology";
import {
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Layers,
  Repeat,
  Compass,
  ArrowUp,
  ArrowDown,
  RotateCcw,
  Sparkles,
  HelpCircle,
  ArrowRight,
} from "lucide-react";
import { calculateMpe } from "../utils/oimlEngine";

interface DataEntryDashboardProps {
  instrument: InstrumentProfile;
  readings: ReadingItem[];
  computation: MetrologyComputation;
  onUpdateReadings: (readings: ReadingItem[]) => void;
  onProceedToReport: () => void;
}

export const DataEntryDashboard: React.FC<DataEntryDashboardProps> = ({
  instrument,
  readings,
  computation,
  onUpdateReadings,
  onProceedToReport,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<
    "all" | "load" | "eccentricity" | "repeatability"
  >("load");
  const [filterStatus, setFilterStatus] = useState<"all" | "fail" | "pass">(
    "all",
  );

  // Handle single reading update
  const handleUpdateItem = (id: string, updates: Partial<ReadingItem>) => {
    const next = readings.map((r) => (r.id === id ? { ...r, ...updates } : r));
    onUpdateReadings(next);
  };

  // Add a new row
  const handleAddRow = (
    load: number = instrument.maxCapacity * 0.5,
    direction: LoadDirection = "increasing",
    position: PlatformPosition = "center",
    repeatNumber: number = 1,
  ) => {
    const newItem: ReadingItem = {
      id: "row-" + Date.now() + "-" + Math.random().toString(36).substr(2, 4),
      load: Number(load.toFixed(4)),
      reading: Number(load.toFixed(4)),
      direction,
      repeatNumber,
      position,
    };
    onUpdateReadings([...readings, newItem]);
  };

  // Delete row
  const handleDeleteRow = (id: string) => {
    onUpdateReadings(readings.filter((r) => r.id !== id));
  };

  // Pre-fill Standard OIML R-76 10-point test schedule
  const handleGenerateOimlSchedule = (pointsCount: 5 | 10) => {
    const max = instrument.maxCapacity;
    const min = instrument.minCapacity;
    const newReadings: ReadingItem[] = [];

    // Ascending load points
    const stepFractions =
      pointsCount === 10
        ? [0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0]
        : [0, 0.25, 0.5, 0.75, 1.0];

    const loads = stepFractions.map((f) =>
      f === 0 ? 0 : Math.max(min, f * max),
    );

    // 1. Increasing run
    loads.forEach((ld, idx) => {
      newReadings.push({
        id: `gen-inc-${idx}`,
        load: Number(ld.toFixed(4)),
        reading: Number(ld.toFixed(4)),
        direction: "increasing",
        repeatNumber: 1,
        position: "center",
      });
    });

    // 2. Decreasing run (hysteresis check)
    [...loads].reverse().forEach((ld, idx) => {
      if (ld > 0) {
        newReadings.push({
          id: `gen-dec-${idx}`,
          load: Number(ld.toFixed(4)),
          reading: Number(ld.toFixed(4)),
          direction: "decreasing",
          repeatNumber: 1,
          position: "center",
        });
      }
    });

    // 3. Repeatability (3 runs at 0.5 Max & 1.0 Max)
    [2, 3].forEach((run) => {
      [0.5 * max, max].forEach((ld, lIdx) => {
        newReadings.push({
          id: `gen-rep-${run}-${lIdx}`,
          load: Number(ld.toFixed(4)),
          reading: Number(ld.toFixed(4)),
          direction: "increasing",
          repeatNumber: run,
          position: "center",
        });
      });
    });

    // 4. Eccentricity at 1/3 Max on 4 corners + center
    const eccLoad = Number((max / 3).toFixed(4));
    (
      [
        "center",
        "front-left",
        "front-right",
        "back-left",
        "back-right",
      ] as PlatformPosition[]
    ).forEach((pos, idx) => {
      newReadings.push({
        id: `gen-ecc-${idx}`,
        load: eccLoad,
        reading: eccLoad,
        direction: "increasing",
        repeatNumber: 1,
        position: pos,
      });
    });

    onUpdateReadings(newReadings);
  };

  // Filter readings based on active subTab
  const filteredReadings = readings
    .filter((r) => {
      if (activeSubTab === "eccentricity") {
        return (
          r.position !== "center" ||
          (r.load === computation.eccentricitySummary.testLoad &&
            r.repeatNumber === 1)
        );
      }
      if (activeSubTab === "repeatability") {
        return (
          r.repeatNumber > 1 ||
          (r.direction === "increasing" &&
            readings.filter((x) => x.load === r.load && x.position === "center")
              .length > 1)
        );
      }
      if (activeSubTab === "load") {
        return r.position === "center" || !r.position;
      }
      return true;
    })
    .filter((r) => {
      const point = computation.pointResults.find(
        (p) =>
          p.load === r.load &&
          p.reading === r.reading &&
          p.direction === r.direction,
      );
      if (!point) return true;
      if (filterStatus === "pass") return point.passed;
      if (filterStatus === "fail") return !point.passed;
      return true;
    });

  return (
    <div className="max-w-[1500px] mx-auto space-y-6 pb-12">
      {/* Top Testing Overview Strip */}
      <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-50 text-blue-700 border border-blue-200">
              OIML R 76-1 SECTION A.4 TESTING ENGINE
            </span>
            <span className="text-xs text-[#64748B]">
              Class {instrument.accuracyClass} · Max {instrument.maxCapacity}{" "}
              {instrument.unit} · e = {instrument.verificationScaleIntervalE}{" "}
              {instrument.unit}
            </span>
          </div>
          <h2 className="text-lg font-semibold text-[#0F172A] mt-1">
            Metrological Test Parameters & Data Entry
          </h2>
          <p className="text-xs text-[#64748B] mt-0.5">
            Log raw indicator readings across standard test protocols:
            Eccentricity, Repeatability, and Load performance.
          </p>
        </div>

        {/* Quick statistics badges */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-2 bg-slate-50 border border-slate-200 rounded text-center">
            <div className="text-[10px] text-[#64748B] uppercase tracking-wider font-semibold">
              Total Records
            </div>
            <div className="text-base font-mono font-bold text-[#0F172A]">
              {readings.length}
            </div>
          </div>
          <div className="px-3.5 py-2 bg-emerald-50 border border-emerald-200 rounded text-center">
            <div className="text-[10px] text-emerald-700 uppercase tracking-wider font-semibold">
              Conforming
            </div>
            <div className="text-base font-mono font-bold text-emerald-800">
              {computation.pointResults.filter((p) => p.passed).length}
            </div>
          </div>
          <div className="px-3.5 py-2 bg-red-50 border border-red-200 rounded text-center">
            <div className="text-[10px] text-red-700 uppercase tracking-wider font-semibold">
              Deviations
            </div>
            <div className="text-base font-mono font-bold text-red-800">
              {computation.pointResults.filter((p) => !p.passed).length}
            </div>
          </div>
        </div>
      </div>

      {/* Sub-Nav Segmented Controls & Data Generation Tools */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 border border-[#E2E8F0] rounded-lg shadow-subtle">
        <div className="flex items-center space-x-1.5 overflow-x-auto">
          <button
            onClick={() => setActiveSubTab("load")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activeSubTab === "load"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Load Performance (A.4.2)</span>
          </button>

          <button
            onClick={() => setActiveSubTab("eccentricity")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activeSubTab === "eccentricity"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Eccentricity / Corner Load (A.4.7)</span>
          </button>

          <button
            onClick={() => setActiveSubTab("repeatability")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activeSubTab === "repeatability"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <Repeat className="w-3.5 h-3.5" />
            <span>Repeatability (A.4.4)</span>
          </button>

          <button
            onClick={() => setActiveSubTab("all")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activeSubTab === "all"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>All Readings ({readings.length})</span>
          </button>
        </div>

        <div className="flex items-center space-x-2 self-end sm:self-auto">
          {/* Quick Schedule Generators */}
          <div className="relative group">
            <button
              type="button"
              className="flex items-center space-x-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200 rounded hover:bg-slate-100"
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>OIML Schedule Pre-fill</span>
            </button>
            <div className="hidden group-hover:block absolute right-0 mt-1 w-52 bg-white border border-[#E2E8F0] rounded shadow-lg py-1 z-30">
              <button
                onClick={() => handleGenerateOimlSchedule(10)}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 text-slate-700"
              >
                Standard 10-Point Schedule
              </button>
              <button
                onClick={() => handleGenerateOimlSchedule(5)}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 text-slate-700"
              >
                Quick 5-Point Schedule
              </button>
            </div>
          </div>

          <button
            onClick={() => handleAddRow()}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded transition-colors shadow-subtle"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Row</span>
          </button>
        </div>
      </div>

      {/* SPECIAL INTERACTIVE PANEL: Eccentricity Visual Diagram (When in Eccentricity or All view) */}
      {(activeSubTab === "eccentricity" || activeSubTab === "all") && (
        <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 mb-4 border-b border-[#E2E8F0]">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                  OIML R 76-1 Section A.4.7: Eccentricity (Corner Load) Test
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  Target Load: ≈ 1/3 Max (
                  {computation.eccentricitySummary.testLoad} {instrument.unit})
                </span>
              </div>
              <p className="text-xs text-[#64748B] mt-0.5">
                Load placed in center and four platform quadrants. Max
                difference between position errors must not exceed MPE.
              </p>
            </div>

            <div
              className={`mt-2 md:mt-0 px-3 py-1.5 rounded text-xs font-mono font-semibold border ${
                computation.eccentricitySummary.passed
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-red-50 text-red-800 border-red-200"
              }`}
            >
              Max Deviation: {computation.eccentricitySummary.maxDeviation}{" "}
              {instrument.unit} | Status:{" "}
              {computation.eccentricitySummary.passed ? "PASS" : "FAIL"}
            </div>
          </div>

          {/* Interactive Platform Quadrant Layout */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {computation.eccentricitySummary.readings.map((item) => {
              const matchingRow = readings.find(
                (r) =>
                  r.position === item.position &&
                  r.load === computation.eccentricitySummary.testLoad,
              );
              return (
                <div
                  key={item.position}
                  className={`p-3 rounded border transition-all ${
                    item.position === "center"
                      ? "bg-blue-50/40 border-blue-300 ring-1 ring-blue-400"
                      : "bg-slate-50/60 border-slate-200"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] font-medium text-slate-600 mb-1.5">
                    <span className="font-semibold text-slate-800">
                      {item.label}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-1 rounded ${
                        item.passed
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {item.passed ? "PASS" : "FAIL"}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-slate-500">
                        Reading:
                      </span>
                      <input
                        type="number"
                        step="any"
                        value={matchingRow ? matchingRow.reading : item.reading}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value) || 0;
                          if (matchingRow) {
                            handleUpdateItem(matchingRow.id, { reading: val });
                          } else {
                            handleAddRow(
                              computation.eccentricitySummary.testLoad,
                              "increasing",
                              item.position,
                              1,
                            );
                          }
                        }}
                        className="w-20 px-1.5 py-0.5 text-right font-mono text-xs rounded border border-slate-300 bg-white"
                      />
                    </div>
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-500">Error:</span>
                      <span
                        className={`font-semibold ${item.error === 0 ? "text-slate-600" : item.error > 0 ? "text-blue-700" : "text-amber-700"}`}
                      >
                        {item.error > 0 ? "+" : ""}
                        {item.error.toFixed(4)}
                      </span>
                    </div>
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-500">MPE:</span>
                      <span className="text-slate-700">
                        ±{item.mpe.toFixed(4)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SPECIAL INTERACTIVE PANEL: Repeatability Statistics (When in Repeatability or All view) */}
      {(activeSubTab === "repeatability" || activeSubTab === "all") &&
        computation.repeatabilitySummary.length > 0 && (
          <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle">
            <div className="pb-3 mb-4 border-b border-[#E2E8F0] flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    OIML R 76-1 Section A.4.4: Repeatability Metrological
                    Evaluation
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                    Tolerance: Max Range ≤ MPE
                  </span>
                </div>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Evaluation of repeated measurements at identical load steps
                  under identical conditions.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {computation.repeatabilitySummary.map((rep) => (
                <div
                  key={rep.load}
                  className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-2"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                    <span className="font-semibold text-slate-800">
                      Load Point: {rep.load} {instrument.unit} (
                      {rep.runs.length} Runs)
                    </span>
                    <span
                      className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
                        rep.passed
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : "bg-red-50 text-red-800 border-red-200"
                      }`}
                    >
                      {rep.passed ? "CONFORMING" : "NON-CONFORMING"}
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-2 font-mono text-[11px]">
                    <div>
                      <span className="text-slate-500 block text-[10px]">
                        MEAN (x̄)
                      </span>
                      <span className="font-medium text-slate-800">
                        {rep.mean}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">
                        STDEV (s)
                      </span>
                      <span className="font-medium text-slate-800">
                        {rep.standardDeviation}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">
                        RANGE (R)
                      </span>
                      <span className="font-medium text-slate-800">
                        {rep.maxRange}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">
                        MPE LIMIT
                      </span>
                      <span className="font-medium text-slate-800">
                        ±{rep.mpe}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Main High-Density Data Table */}
      <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg shadow-subtle overflow-hidden">
        {/* Table Toolbar */}
        <div className="px-5 py-3.5 bg-white border-b border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#0F172A]">
              Test Readings Registry
            </span>
            <span className="text-xs text-[#64748B] font-mono">
              ({filteredReadings.length} of {readings.length} displayed)
            </span>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-[#64748B]">Status Filter:</span>
            <div className="inline-flex rounded-md border border-slate-200 p-0.5 bg-slate-50">
              <button
                onClick={() => setFilterStatus("all")}
                className={`px-2.5 py-0.5 text-xs rounded transition-colors ${
                  filterStatus === "all"
                    ? "bg-white shadow-sm font-medium text-slate-800"
                    : "text-slate-600"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterStatus("pass")}
                className={`px-2.5 py-0.5 text-xs rounded transition-colors ${
                  filterStatus === "pass"
                    ? "bg-white shadow-sm font-medium text-emerald-700"
                    : "text-slate-600"
                }`}
              >
                Pass Only
              </button>
              <button
                onClick={() => setFilterStatus("fail")}
                className={`px-2.5 py-0.5 text-xs rounded transition-colors ${
                  filterStatus === "fail"
                    ? "bg-white shadow-sm font-medium text-red-700"
                    : "text-slate-600"
                }`}
              >
                Non-Conforming
              </button>
            </div>
          </div>
        </div>

        {/* Dense Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B] font-medium font-sans">
                <th className="py-2.5 px-3.5 w-12 text-center">#</th>
                <th className="py-2.5 px-3">Test Load ({instrument.unit})</th>
                <th className="py-2.5 px-3">
                  Observed Reading ({instrument.unit})
                </th>
                <th className="py-2.5 px-3">Direction</th>
                <th className="py-2.5 px-3">Position</th>
                <th className="py-2.5 px-3">Run #</th>
                <th className="py-2.5 px-3 font-mono">
                  Error E ({instrument.unit})
                </th>
                <th className="py-2.5 px-3 font-mono">
                  OIML MPE ({instrument.unit})
                </th>
                <th className="py-2.5 px-3 font-mono">|E| / MPE Ratio</th>
                <th className="py-2.5 px-3 text-center">Conformity</th>
                <th className="py-2.5 px-3 w-14 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0] text-[#0F172A]">
              {filteredReadings.map((r, index) => {
                const mpe = calculateMpe(
                  r.load,
                  instrument.verificationScaleIntervalE,
                  instrument.accuracyClass,
                );
                const error = r.reading - r.load;
                const passed = Math.abs(error) <= mpe + 1e-9;
                const ratio =
                  mpe > 0 ? Math.min(2.0, Math.abs(error) / mpe) : 0;

                return (
                  <tr
                    key={r.id}
                    className={`hover:bg-slate-50/80 transition-colors font-mono ${
                      !passed ? "bg-red-50/20" : ""
                    }`}
                  >
                    <td className="py-2 px-3 text-center text-slate-400 font-sans text-[11px]">
                      {index + 1}
                    </td>

                    {/* Test Load Input */}
                    <td className="py-2 px-3">
                      <input
                        type="number"
                        step="any"
                        value={r.load}
                        onChange={(e) =>
                          handleUpdateItem(r.id, {
                            load: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-24 px-2 py-1 text-xs rounded border border-[#E2E8F0] focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      />
                    </td>

                    {/* Reading Input */}
                    <td className="py-2 px-3">
                      <input
                        type="number"
                        step="any"
                        value={r.reading}
                        onChange={(e) =>
                          handleUpdateItem(r.id, {
                            reading: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-24 px-2 py-1 text-xs font-semibold rounded border border-[#E2E8F0] focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      />
                    </td>

                    {/* Direction Selector */}
                    <td className="py-2 px-3 font-sans">
                      <button
                        type="button"
                        onClick={() =>
                          handleUpdateItem(r.id, {
                            direction:
                              r.direction === "increasing"
                                ? "decreasing"
                                : "increasing",
                          })
                        }
                        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-medium border ${
                          r.direction === "increasing"
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {r.direction === "increasing" ? (
                          <>
                            <ArrowUp className="w-3 h-3" />
                            <span>Inc (↑)</span>
                          </>
                        ) : (
                          <>
                            <ArrowDown className="w-3 h-3" />
                            <span>Dec (↓)</span>
                          </>
                        )}
                      </button>
                    </td>

                    {/* Position Selector */}
                    <td className="py-2 px-3 font-sans">
                      <select
                        value={r.position || "center"}
                        onChange={(e) =>
                          handleUpdateItem(r.id, {
                            position: e.target.value as PlatformPosition,
                          })
                        }
                        className="px-2 py-1 text-xs rounded border border-[#E2E8F0] bg-white text-slate-700"
                      >
                        <option value="center">Center</option>
                        <option value="front-left">Front-Left</option>
                        <option value="front-right">Front-Right</option>
                        <option value="back-left">Back-Left</option>
                        <option value="back-right">Back-Right</option>
                      </select>
                    </td>

                    {/* Repeat Number */}
                    <td className="py-2 px-3">
                      <input
                        type="number"
                        min="1"
                        max="20"
                        value={r.repeatNumber}
                        onChange={(e) =>
                          handleUpdateItem(r.id, {
                            repeatNumber: parseInt(e.target.value) || 1,
                          })
                        }
                        className="w-12 px-1.5 py-1 text-xs text-center rounded border border-[#E2E8F0] bg-white"
                      />
                    </td>

                    {/* Calculated Error */}
                    <td className="py-2 px-3">
                      <span
                        className={`font-semibold ${
                          error === 0
                            ? "text-slate-600"
                            : error > 0
                              ? "text-blue-700"
                              : "text-amber-700"
                        }`}
                      >
                        {error > 0 ? "+" : ""}
                        {error.toFixed(4)}
                      </span>
                    </td>

                    {/* OIML MPE */}
                    <td className="py-2 px-3 text-slate-600">
                      ±{mpe.toFixed(4)}
                    </td>

                    {/* Ratio Bar */}
                    <td className="py-2 px-3">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full ${
                              ratio <= 0.8
                                ? "bg-emerald-500"
                                : ratio <= 1.0
                                  ? "bg-amber-500"
                                  : "bg-red-500"
                            }`}
                            style={{
                              width: `${Math.min(100, (ratio / 1.0) * 100)}%`,
                            }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {(ratio * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>

                    {/* Conformity Badge */}
                    <td className="py-2 px-3 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-sans font-semibold tracking-wide border ${
                          passed
                            ? "bg-[#ECFDF5] text-[#059669] border-emerald-200"
                            : "bg-[#FEF2F2] text-[#DC2626] border-red-200"
                        }`}
                      >
                        {passed ? "PASS" : "FAIL"}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="py-2 px-3 text-center">
                      <button
                        onClick={() => handleDeleteRow(r.id)}
                        className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
                        title="Delete reading"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Table Bottom Navigation and Quick Proceed Button */}
        <div className="p-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs text-[#64748B]">
            <span>
              Tip: Modifying any load or reading recalculates uncertainty and
              report preview instantly.
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => handleAddRow()}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-50 transition-colors"
            >
              + Add Load Point
            </button>
            <button
              onClick={onProceedToReport}
              className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded transition-colors shadow-subtle"
            >
              <span>View Computations & Official Report</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
