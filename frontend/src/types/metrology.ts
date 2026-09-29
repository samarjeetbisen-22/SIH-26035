export type AccuracyClass = 'I' | 'II' | 'III' | 'IIII';

export type LoadDirection = 'increasing' | 'decreasing';

export type PlatformPosition = 'center' | 'front-left' | 'front-right' | 'back-left' | 'back-right';

export interface InstrumentProfile {
  manufacturer: string;
  model: string;
  serialNumber: string;
  typeApprovalNo: string;
  accuracyClass: AccuracyClass;
  maxCapacity: number; // in kg (or selected unit)
  minCapacity: number; // in kg
  verificationScaleIntervalE: number; // e in kg
  actualScaleIntervalD: number; // d in kg
  unit: 'kg' | 'g' | 'mg' | 't';
  yearOfManufacture: number;
  countryOfOrigin: string;
  tareCapacity: number;
}

export interface TestConditions {
  temperatureC: number;
  humidityPercent: number;
  barometricPressureHpa: number;
  gravityMps2: number;
  referenceMassStandard: string; // e.g. Class F1 / Class E2
  standardsTraceabilityNo: string;
  testLocation: string;
  inspectorName: string;
  inspectorId: string;
  testDate: string;
}

export interface ReadingItem {
  id: string;
  load: number;
  reading: number;
  direction: LoadDirection;
  repeatNumber: number;
  position: PlatformPosition;
  testType?: 'LOAD' | 'ECCENTRICITY' | 'REPEATABILITY';
}

export interface PointResult {
  load: number;
  reading: number;
  direction: LoadDirection;
  error: number;
  mpe: number;
  ratio: number; // |error| / mpe
  passed: boolean;
  position?: PlatformPosition;
  repeatNumber?: number;
}

export interface EccentricityResult {
  testLoad: number;
  readings: {
    position: PlatformPosition;
    label: string;
    reading: number;
    error: number;
    mpe: number;
    passed: boolean;
  }[];
  maxDeviation: number;
  passed: boolean;
}

export interface RepeatabilityResult {
  load: number;
  runs: {
    runIndex: number;
    reading: number;
    error: number;
  }[];
  mean: number;
  standardDeviation: number;
  maxRange: number;
  mpe: number;
  passed: boolean;
}

export interface MetrologyComputation {
  repeatabilityError: number;
  linearityError: number;
  hysteresisError: number;
  eccentricityError: number;
  combinedUncertainty: number; // u_c
  expandedUncertainty: number; // U = k * u_c (k=2)
  pointResults: PointResult[];
  eccentricitySummary: EccentricityResult;
  repeatabilitySummary: RepeatabilityResult[];
  overallPass: boolean;
  complianceScore: number; // 0 - 100%
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  verificationHash: string;
  scaleIntervalsN: number; // Max / e
}

export interface AuditHistoryRecord {
  report_id: string;
  instrument_serial: string;
  instrument_model: string;
  capacity: number;
  class: string;
  conformity: number;
  compliance_score: number;
  risk_level: string;
  created_at: string;
  inspector_name: string;
}

