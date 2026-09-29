import React from "react";
import {
  InstrumentProfile,
  TestConditions,
  AccuracyClass,
} from "../types/metrology";
import {
  Building2,
  Cpu,
  Thermometer,
  ShieldCheck,
  Info,
  Check,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Save,
  Trash2,
  Plus,
  Database,
} from "lucide-react";
import { PRESET_PROFILES } from "../data/mockData";

interface InstrumentIntakeFormProps {
  instrument: InstrumentProfile;
  conditions: TestConditions;
  onUpdateInstrument: (updated: Partial<InstrumentProfile>) => void;
  onUpdateConditions: (updated: Partial<TestConditions>) => void;
  onProceed: () => void;
  onSelectPreset: (presetId: string) => void;
  savedInstruments?: any[];
  onSelectSavedInstrument?: (inst: any) => void;
  onSaveInstrument?: () => Promise<void>;
  onDeleteInstrument?: (instId: string) => Promise<void>;
  onNewInstrument?: () => void;
  isSavingInstrument?: boolean;
}

export const InstrumentIntakeForm: React.FC<InstrumentIntakeFormProps> = ({
  instrument,
  conditions,
  onUpdateInstrument,
  onUpdateConditions,
  onProceed,
  onSelectPreset,
  savedInstruments = [],
  onSelectSavedInstrument,
  onSaveInstrument,
  onDeleteInstrument,
  onNewInstrument,
  isSavingInstrument = false,
}) => {
  const nIntervals =
    instrument.verificationScaleIntervalE > 0
      ? Math.round(
          instrument.maxCapacity / instrument.verificationScaleIntervalE,
        )
      : 0;

  // Validation rules according to OIML R 76-1 Table 3
  const getClassRules = (c: AccuracyClass) => {
    switch (c) {
      case "I":
        return {
          name: "Special Accuracy (Analytical)",
          nMin: 50000,
          nMax: Infinity,
          typicalUse:
            "Micro-balances, analytical laboratory standards, precious gems",
          minE: "0.001 g (1 mg)",
        };
      case "II":
        return {
          name: "High Accuracy (Precision)",
          nMin: 100,
          nMax: 100000,
          typicalUse:
            "Pharmaceutical, gold & jewellery balances, chemical testing",
          minE: "0.001 g to 0.05 g",
        };
      case "III":
        return {
          name: "Medium Accuracy (Commercial / Industrial)",
          nMin: 500,
          nMax: 10000,
          typicalUse:
            "Commercial counter scales, platform scales, warehouse weighing",
          minE: "0.1 g or greater",
        };
      case "IIII":
        return {
          name: "Ordinary Accuracy (Heavy Industrial)",
          nMin: 100,
          nMax: 1000,
          typicalUse: "Weighbridges, crane scales, bulk vessel weighing",
          minE: "5 g or greater",
        };
    }
  };

  const classRule = getClassRules(instrument.accuracyClass);
  const isNValid =
    nIntervals >= classRule.nMin &&
    (classRule.nMax === Infinity || nIntervals <= classRule.nMax);

  return (
    <div className="max-w-[1400px] mx-auto space-y-6 pb-12">
      {/* Top Banner / Quick Fill Presets */}
      <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-50 text-blue-700 border border-blue-200">
              OIML R-76 SECTION 3 COMPLIANT INTAKE
            </span>
            <span className="text-xs text-[#64748B]">
              Legal Metrology Form 1-B
            </span>
          </div>
          <h2 className="text-lg font-semibold text-[#0F172A] mt-1">
            Instrument Specification & Metrological Profiling
          </h2>
          <p className="text-xs text-[#64748B] mt-0.5">
            Configure manufacturer declarations, verification intervals, and
            environmental baseline conditions prior to test execution.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
          {savedInstruments && savedInstruments.length > 0 && (
            <div className="flex items-center gap-1.5 mr-2">
              <span className="text-xs text-slate-500 font-medium">
                Saved Scales:
              </span>
              <select
                value={instrument.id || ""}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "NEW") {
                    onNewInstrument?.();
                  } else {
                    const found = savedInstruments.find((s) => s.id === val);
                    if (found && onSelectSavedInstrument) onSelectSavedInstrument(found);
                  }
                }}
                className="text-xs bg-white border border-slate-300 rounded px-2 py-1.5 font-mono text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
              >
                <option value="">-- Choose Scale ({savedInstruments.length}) --</option>
                {savedInstruments.map((si) => (
                  <option key={si.id} value={si.id}>
                    {si.serial_number || si.serialNumber} - {si.model} ({si.status || "REGISTERED"})
                  </option>
                ))}
              </select>
            </div>
          )}

          {onNewInstrument && (
            <button
              type="button"
              onClick={onNewInstrument}
              className="px-2.5 py-1.5 text-xs font-mono font-medium rounded border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors flex items-center space-x-1"
              title="Start registration for a new scale"
            >
              <Plus className="w-3 h-3" />
              <span>New Scale</span>
            </button>
          )}

          <span className="text-xs text-slate-400 hidden md:inline">|</span>

          <span className="text-xs text-slate-500 font-medium">
            Quick Presets:
          </span>
          {PRESET_PROFILES.map((preset) => (
            <button
              key={preset.id}
              onClick={() => onSelectPreset(preset.id)}
              className="px-2 py-1.5 text-xs font-mono font-medium rounded border border-slate-200 bg-slate-50 text-slate-700 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
            >
              {preset.instrument.accuracyClass} ({preset.instrument.maxCapacity}
              {preset.instrument.unit})
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Multi-Section Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* SECTION A: Manufacturer & Device Identity */}
          <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-6 shadow-subtle">
            <div className="flex items-center space-x-2.5 pb-4 mb-5 border-b border-[#E2E8F0]">
              <div className="w-7 h-7 rounded bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
                <Building2 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#0F172A]">
                  Section A: Manufacturer & Model Identification
                </h3>
                <p className="text-xs text-[#64748B]">
                  Statutory identification per Legal Metrology (Approval of
                  Models) Rules, 2011
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Manufacturer Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={instrument.manufacturer}
                  onChange={(e) =>
                    onUpdateInstrument({ manufacturer: e.target.value })
                  }
                  placeholder="e.g. Essae Teraoka Pvt. Ltd."
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Model Designation <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={instrument.model}
                  onChange={(e) =>
                    onUpdateInstrument({ model: e.target.value })
                  }
                  placeholder="e.g. DS-852"
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Instrument Serial Number{" "}
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={instrument.serialNumber}
                  onChange={(e) =>
                    onUpdateInstrument({ serialNumber: e.target.value })
                  }
                  placeholder="e.g. ET-DS852-2026-0471"
                  className="w-full px-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Type Approval Certificate No.
                </label>
                <input
                  type="text"
                  value={instrument.typeApprovalNo}
                  onChange={(e) =>
                    onUpdateInstrument({ typeApprovalNo: e.target.value })
                  }
                  placeholder="e.g. IND/LM/09/2026/0471"
                  className="w-full px-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Year of Manufacture
                </label>
                <input
                  type="number"
                  value={instrument.yearOfManufacture}
                  onChange={(e) =>
                    onUpdateInstrument({
                      yearOfManufacture: parseInt(e.target.value) || 2026,
                    })
                  }
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Country of Origin
                </label>
                <input
                  type="text"
                  value={instrument.countryOfOrigin}
                  onChange={(e) =>
                    onUpdateInstrument({ countryOfOrigin: e.target.value })
                  }
                  placeholder="e.g. India"
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>
            </div>
          </div>

          {/* SECTION B: Metrological Parameters */}
          <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-6 shadow-subtle">
            <div className="flex items-center space-x-2.5 pb-4 mb-5 border-b border-[#E2E8F0]">
              <div className="w-7 h-7 rounded bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
                <Cpu className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#0F172A]">
                  Section B: Metrological Characteristics & OIML Class
                </h3>
                <p className="text-xs text-[#64748B]">
                  Defines verification boundaries, scale intervals (e & d), and
                  maximum weighing capacity
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-5">
              {/* Accuracy Class Selector Cards */}
              {(["I", "II", "III", "IIII"] as AccuracyClass[]).map((cls) => (
                <button
                  key={cls}
                  type="button"
                  onClick={() => onUpdateInstrument({ accuracyClass: cls })}
                  className={`p-3 text-left rounded border transition-all ${
                    instrument.accuracyClass === cls
                      ? "border-[#2563EB] bg-blue-50/50 ring-1 ring-blue-500"
                      : "border-[#E2E8F0] bg-white hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-[#0F172A]">
                      Class {cls}
                    </span>
                    {instrument.accuracyClass === cls && (
                      <span className="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px]">
                        <Check className="w-2.5 h-2.5 stroke-[3]" />
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-[#64748B] mt-1 line-clamp-1">
                    {getClassRules(cls).name}
                  </div>
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Max Capacity (Max) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    value={instrument.maxCapacity}
                    onChange={(e) =>
                      onUpdateInstrument({
                        maxCapacity: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full pr-12 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    {instrument.unit}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Min Capacity (Min)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    value={instrument.minCapacity}
                    onChange={(e) =>
                      onUpdateInstrument({
                        minCapacity: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full pr-12 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    {instrument.unit}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Weighing Unit
                </label>
                <select
                  value={instrument.unit}
                  onChange={(e) =>
                    onUpdateInstrument({ unit: e.target.value as any })
                  }
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                >
                  <option value="kg">Kilograms (kg)</option>
                  <option value="g">Grams (g)</option>
                  <option value="mg">Milligrams (mg)</option>
                  <option value="t">Metric Tonnes (t)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Verification Scale Interval (e){" "}
                  <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    value={instrument.verificationScaleIntervalE}
                    onChange={(e) =>
                      onUpdateInstrument({
                        verificationScaleIntervalE:
                          parseFloat(e.target.value) || 0.001,
                      })
                    }
                    className="w-full pr-12 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    {instrument.unit}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Actual Scale Interval (d)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    value={instrument.actualScaleIntervalD}
                    onChange={(e) =>
                      onUpdateInstrument({
                        actualScaleIntervalD:
                          parseFloat(e.target.value) || 0.001,
                      })
                    }
                    className="w-full pr-12 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    {instrument.unit}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Tare Range (T)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    value={instrument.tareCapacity}
                    onChange={(e) =>
                      onUpdateInstrument({
                        tareCapacity: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full pr-12 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    {instrument.unit}
                  </span>
                </div>
              </div>
            </div>

            {/* Calculated Scale Intervals helper banner */}
            <div className="mt-5 p-3.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Info className="w-4 h-4 text-slate-400 flex-shrink-0" />
                <div className="text-xs">
                  <span className="text-[#64748B]">
                    Calculated Verification Intervals (n = Max / e):{" "}
                  </span>
                  <span className="font-mono font-semibold text-[#0F172A]">
                    {nIntervals.toLocaleString()}
                  </span>
                  <span className="text-slate-400 mx-2">|</span>
                  <span className="text-[#64748B]">
                    OIML Class {instrument.accuracyClass} Range:{" "}
                  </span>
                  <span className="font-mono text-slate-700">
                    {classRule.nMin.toLocaleString()} to{" "}
                    {classRule.nMax === Infinity
                      ? "Unlimited"
                      : classRule.nMax.toLocaleString()}
                  </span>
                </div>
              </div>

              <div
                className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded border ${
                  isNValid
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-amber-50 text-amber-700 border-amber-200"
                }`}
              >
                {isNValid
                  ? "VALID FOR CLASS " + instrument.accuracyClass
                  : "OUTSIDE NOMINAL RANGE"}
              </div>
            </div>
          </div>

          {/* SECTION C: Environmental & Standards Traceability */}
          <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-6 shadow-subtle">
            <div className="flex items-center space-x-2.5 pb-4 mb-5 border-b border-[#E2E8F0]">
              <div className="w-7 h-7 rounded bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
                <Thermometer className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#0F172A]">
                  Section C: Environmental & Calibration Reference Conditions
                </h3>
                <p className="text-xs text-[#64748B]">
                  Monitored laboratory conditions for buoyancy and gravity
                  compensations
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Temperature (°C)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    value={conditions.temperatureC}
                    onChange={(e) =>
                      onUpdateConditions({
                        temperatureC: parseFloat(e.target.value) || 20.0,
                      })
                    }
                    className="w-full pr-8 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    °C
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Relative Humidity (%)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={conditions.humidityPercent}
                    onChange={(e) =>
                      onUpdateConditions({
                        humidityPercent: parseFloat(e.target.value) || 50,
                      })
                    }
                    className="w-full pr-8 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    %
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Pressure (hPa)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    value={conditions.barometricPressureHpa}
                    onChange={(e) =>
                      onUpdateConditions({
                        barometricPressureHpa:
                          parseFloat(e.target.value) || 1013.25,
                      })
                    }
                    className="w-full pr-10 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-3 top-2 text-xs font-mono text-slate-400">
                    hPa
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Local Gravity g (m/s²)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.0001"
                    value={conditions.gravityMps2}
                    onChange={(e) =>
                      onUpdateConditions({
                        gravityMps2: parseFloat(e.target.value) || 9.80665,
                      })
                    }
                    className="w-full pr-12 pl-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                  />
                  <span className="absolute right-2.5 top-2 text-[11px] font-mono text-slate-400">
                    m/s²
                  </span>
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Reference Standard Weights Employed
                </label>
                <input
                  type="text"
                  value={conditions.referenceMassStandard}
                  onChange={(e) =>
                    onUpdateConditions({
                      referenceMassStandard: e.target.value,
                    })
                  }
                  placeholder="e.g. OIML Class F1 Stainless Steel Standards"
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  National / Traceability Certificate No.
                </label>
                <input
                  type="text"
                  value={conditions.standardsTraceabilityNo}
                  onChange={(e) =>
                    onUpdateConditions({
                      standardsTraceabilityNo: e.target.value,
                    })
                  }
                  placeholder="e.g. NPLI/LM/MASS/2026/0942"
                  className="w-full px-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>
            </div>
          </div>

          {/* SECTION D: Verifying Officers & Inspection Authority */}
          <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-6 shadow-subtle">
            <div className="flex items-center space-x-2.5 pb-4 mb-5 border-b border-[#E2E8F0]">
              <div className="w-7 h-7 rounded bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#0F172A]">
                  Section D: Inspection Agency & Certifying Officer
                </h3>
                <p className="text-xs text-[#64748B]">
                  Authorized Legal Metrology Officer and Testing Facility
                  Details
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Testing Facility / Laboratory Name
                </label>
                <input
                  type="text"
                  value={conditions.testLocation}
                  onChange={(e) =>
                    onUpdateConditions({ testLocation: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Inspection Date
                </label>
                <input
                  type="date"
                  value={conditions.testDate}
                  onChange={(e) =>
                    onUpdateConditions({ testDate: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Verifying Officer / Inspector Name
                </label>
                <input
                  type="text"
                  value={conditions.inspectorName}
                  onChange={(e) =>
                    onUpdateConditions({ inspectorName: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs font-sans rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#0F172A] mb-1.5">
                  Inspector License / Badge ID
                </label>
                <input
                  type="text"
                  value={conditions.inspectorId}
                  onChange={(e) =>
                    onUpdateConditions({ inspectorId: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs font-mono rounded border border-[#E2E8F0] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white text-slate-800"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right 1 Column: Metrological Summary & Navigation Card */}
        <div className="space-y-6">
          <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-lg p-5 shadow-subtle sticky top-24">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                Profile Summary Card
              </h3>
              {instrument.id ? (
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${
                  instrument.status === 'VERIFIED'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : instrument.status === 'ARCHIVED'
                    ? 'bg-amber-50 text-amber-800 border-amber-300'
                    : 'bg-blue-50 text-blue-700 border-blue-200'
                }`}>
                  {instrument.status || 'REGISTERED'}
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium text-slate-500 bg-slate-100 border border-slate-200">
                  Unsaved Draft
                </span>
              )}
            </div>

            <div className="space-y-3 pb-4 border-b border-[#E2E8F0] text-xs">
              {instrument.id && (
                <div className="flex justify-between items-center">
                  <span className="text-[#64748B]">Scale Record ID:</span>
                  <span className="font-mono text-[11px] font-semibold text-blue-700 truncate max-w-[150px]">
                    {instrument.id}
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Instrument:</span>
                <span className="font-medium text-[#0F172A] text-right truncate max-w-[160px]">
                  {instrument.model || "Unnamed Model"}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Manufacturer:</span>
                <span className="font-medium text-[#0F172A] text-right truncate max-w-[160px]">
                  {instrument.manufacturer || "—"}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">OIML Accuracy Class:</span>
                <span className="px-2 py-0.5 rounded font-mono font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  Class {instrument.accuracyClass}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Max Capacity:</span>
                <span className="font-mono font-medium text-[#0F172A]">
                  {instrument.maxCapacity} {instrument.unit}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Verification Step (e):</span>
                <span className="font-mono font-medium text-[#0F172A]">
                  {instrument.verificationScaleIntervalE} {instrument.unit}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Scale Divisions (n):</span>
                <span className="font-mono font-medium text-[#0F172A]">
                  {nIntervals.toLocaleString()}
                </span>
              </div>
            </div>

            {/* OIML MPE Step Rules Preview for this class */}
            <div className="py-4 border-b border-[#E2E8F0]">
              <div className="text-[11px] font-semibold text-[#0F172A] mb-2">
                OIML R-76 MPE Thresholds for Class {instrument.accuracyClass}:
              </div>
              <div className="space-y-1.5 text-[11px] font-mono">
                <div className="p-1.5 rounded bg-slate-50 border border-slate-200 flex justify-between">
                  <span className="text-slate-600">
                    0 ≤ m ≤{" "}
                    {instrument.accuracyClass === "I"
                      ? "50,000"
                      : instrument.accuracyClass === "II"
                        ? "5,000"
                        : instrument.accuracyClass === "III"
                          ? "500"
                          : "50"}
                    e:
                  </span>
                  <span className="font-semibold text-emerald-700">
                    ± 0.5 e
                  </span>
                </div>
                <div className="p-1.5 rounded bg-slate-50 border border-slate-200 flex justify-between">
                  <span className="text-slate-600">
                    {instrument.accuracyClass === "I"
                      ? "50k"
                      : instrument.accuracyClass === "II"
                        ? "5k"
                        : instrument.accuracyClass === "III"
                          ? "500"
                          : "50"}{" "}
                    &lt; m ≤{" "}
                    {instrument.accuracyClass === "I"
                      ? "200,000"
                      : instrument.accuracyClass === "II"
                        ? "20,000"
                        : instrument.accuracyClass === "III"
                          ? "2,000"
                          : "200"}
                    e:
                  </span>
                  <span className="font-semibold text-blue-700">± 1.0 e</span>
                </div>
                <div className="p-1.5 rounded bg-slate-50 border border-slate-200 flex justify-between">
                  <span className="text-slate-600">
                    m &gt;{" "}
                    {instrument.accuracyClass === "I"
                      ? "200,000"
                      : instrument.accuracyClass === "II"
                        ? "20,000"
                        : instrument.accuracyClass === "III"
                          ? "2,000"
                          : "200"}
                    e:
                  </span>
                  <span className="font-semibold text-amber-700">± 1.5 e</span>
                </div>
              </div>
            </div>

            <div className="pt-4 space-y-2">
              {onSaveInstrument && (
                <button
                  type="button"
                  onClick={onSaveInstrument}
                  disabled={isSavingInstrument}
                  className="w-full flex items-center justify-center space-x-2 py-2 px-4 rounded text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 transition-colors disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5 text-blue-600" />
                  <span>
                    {isSavingInstrument
                      ? "Saving to Database..."
                      : instrument.id
                      ? "Update Scale in DB"
                      : "Save Scale to Database"}
                  </span>
                </button>
              )}

              {instrument.id && onDeleteInstrument && (
                <button
                  type="button"
                  onClick={() => onDeleteInstrument(instrument.id!)}
                  className="w-full flex items-center justify-center space-x-2 py-1.5 px-3 rounded text-xs font-medium text-red-600 hover:text-red-800 hover:bg-red-50 border border-red-200 transition-colors"
                  title="Archive or delete instrument from database"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete / Archive Scale</span>
                </button>
              )}

              <button
                type="button"
                onClick={onProceed}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded text-xs font-semibold text-white bg-[#2563EB] hover:bg-[#1D4ED8] transition-colors shadow-subtle"
              >
                <span>Save Profile & Proceed to Testing</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <p className="text-[11px] text-center text-[#64748B] mt-2">
                Proceeds to enter eccentricity, repeatability, and load data.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
