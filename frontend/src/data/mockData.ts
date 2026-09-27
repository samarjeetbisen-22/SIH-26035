import { InstrumentProfile, TestConditions, ReadingItem } from '../types/metrology';

export const DEFAULT_INSTRUMENT: InstrumentProfile = {
  manufacturer: 'Essae Teraoka Pvt. Ltd.',
  model: 'DS-852 Heavy-Duty Digital Scale',
  serialNumber: 'ET-DS852-2026-0471',
  typeApprovalNo: 'IND/LM/09/2026/0471',
  accuracyClass: 'III',
  maxCapacity: 15.0,
  minCapacity: 0.04,
  verificationScaleIntervalE: 0.005,
  actualScaleIntervalD: 0.005,
  unit: 'kg',
  yearOfManufacture: 2026,
  countryOfOrigin: 'India',
  tareCapacity: 15.0,
};

export const DEFAULT_CONDITIONS: TestConditions = {
  temperatureC: 25.2,
  humidityPercent: 58,
  barometricPressureHpa: 1012.5,
  gravityMps2: 9.7915,
  referenceMassStandard: 'OIML Class F1 Cast Iron & Stainless Steel Weights',
  standardsTraceabilityNo: 'NPLI/LM/MASS/2026/0942',
  testLocation: 'Regional Reference Standards Laboratory (RRSL), New Delhi',
  inspectorName: 'Rajesh Kumar Sharma',
  inspectorId: 'INS-DL-2024-0087',
  testDate: '2026-09-27',
};

export const DEFAULT_READINGS: ReadingItem[] = [
  // Load Run 1 (Increasing)
  { id: 'r1', load: 0.0, reading: 0.0, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r2', load: 1.0, reading: 1.002, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r3', load: 3.0, reading: 3.003, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r4', load: 5.0, reading: 5.004, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r5', load: 7.5, reading: 7.503, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r6', load: 10.0, reading: 10.005, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r7', load: 12.0, reading: 12.004, direction: 'increasing', repeatNumber: 1, position: 'center' },
  { id: 'r8', load: 15.0, reading: 15.006, direction: 'increasing', repeatNumber: 1, position: 'center' },

  // Repeatability Run 2
  { id: 'r9', load: 0.0, reading: 0.0, direction: 'increasing', repeatNumber: 2, position: 'center' },
  { id: 'r10', load: 1.0, reading: 1.001, direction: 'increasing', repeatNumber: 2, position: 'center' },
  { id: 'r11', load: 5.0, reading: 5.003, direction: 'increasing', repeatNumber: 2, position: 'center' },
  { id: 'r12', load: 10.0, reading: 10.004, direction: 'increasing', repeatNumber: 2, position: 'center' },
  { id: 'r13', load: 15.0, reading: 15.007, direction: 'increasing', repeatNumber: 2, position: 'center' },

  // Repeatability Run 3
  { id: 'r14', load: 0.0, reading: 0.0, direction: 'increasing', repeatNumber: 3, position: 'center' },
  { id: 'r15', load: 5.0, reading: 5.005, direction: 'increasing', repeatNumber: 3, position: 'center' },
  { id: 'r16', load: 10.0, reading: 10.006, direction: 'increasing', repeatNumber: 3, position: 'center' },
  { id: 'r17', load: 15.0, reading: 15.005, direction: 'increasing', repeatNumber: 3, position: 'center' },

  // Decreasing (Hysteresis Check)
  { id: 'r18', load: 15.0, reading: 15.007, direction: 'decreasing', repeatNumber: 1, position: 'center' },
  { id: 'r19', load: 10.0, reading: 10.006, direction: 'decreasing', repeatNumber: 1, position: 'center' },
  { id: 'r20', load: 5.0, reading: 5.005, direction: 'decreasing', repeatNumber: 1, position: 'center' },
  { id: 'r21', load: 1.0, reading: 1.002, direction: 'decreasing', repeatNumber: 1, position: 'center' },
  { id: 'r22', load: 0.0, reading: 0.001, direction: 'decreasing', repeatNumber: 1, position: 'center' },

  // Eccentricity (Corner Load at 1/3 Max = 5.0 kg)
  { id: 'r23', load: 5.0, reading: 5.004, direction: 'increasing', repeatNumber: 1, position: 'front-left' },
  { id: 'r24', load: 5.0, reading: 5.003, direction: 'increasing', repeatNumber: 1, position: 'front-right' },
  { id: 'r25', load: 5.0, reading: 5.006, direction: 'increasing', repeatNumber: 1, position: 'back-left' },
  { id: 'r26', load: 5.0, reading: 5.002, direction: 'increasing', repeatNumber: 1, position: 'back-right' },
];

export const PRESET_PROFILES: {
  id: string;
  name: string;
  classTag: string;
  instrument: InstrumentProfile;
  conditions: TestConditions;
  readings: ReadingItem[];
}[] = [
  {
    id: 'essae-ds852',
    name: 'Essae Teraoka DS-852 (Class III Industrial)',
    classTag: 'Class III · 15 kg',
    instrument: DEFAULT_INSTRUMENT,
    conditions: DEFAULT_CONDITIONS,
    readings: DEFAULT_READINGS,
  },
  {
    id: 'sartorius-micro',
    name: 'Sartorius Cubis II Ultra-Micro (Class I)',
    classTag: 'Class I · 0.0021 kg',
    instrument: {
      manufacturer: 'Sartorius Lab Instruments GmbH',
      model: 'Cubis II Ultra-Microbalance MCA2.7S',
      serialNumber: 'SAR-2026-99042',
      typeApprovalNo: 'PTB-1.12-4091',
      accuracyClass: 'I',
      maxCapacity: 0.0021, // 2.1 g
      minCapacity: 0.00001,
      verificationScaleIntervalE: 0.000001, // 1 mg
      actualScaleIntervalD: 0.0000001, // 0.1 ug
      unit: 'kg',
      yearOfManufacture: 2025,
      countryOfOrigin: 'Germany',
      tareCapacity: 0.0021,
    },
    conditions: {
      temperatureC: 20.0,
      humidityPercent: 45,
      barometricPressureHpa: 1013.2,
      gravityMps2: 9.80665,
      referenceMassStandard: 'OIML Class E1 Micro-weights (DKD-K-02901)',
      standardsTraceabilityNo: 'PTB/DE/2026/MICRO-019',
      testLocation: 'Cleanroom Metrology Suite 4, Bangalore',
      inspectorName: 'Dr. Ananya Sen',
      inspectorId: 'INS-KA-2022-0012',
      testDate: '2026-09-27',
    },
    readings: [
      { id: 's1', load: 0.0, reading: 0.0, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 's2', load: 0.0005, reading: 0.0005001, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 's3', load: 0.0010, reading: 0.0010002, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 's4', load: 0.0015, reading: 0.0015001, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 's5', load: 0.0020, reading: 0.0020003, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 's6', load: 0.0020, reading: 0.0020002, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      { id: 's7', load: 0.0010, reading: 0.0010001, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      { id: 's8', load: 0.0, reading: 0.0000001, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      // Corner tests at 0.0007 kg
      { id: 's9', load: 0.0007, reading: 0.0007001, direction: 'increasing', repeatNumber: 1, position: 'front-left' },
      { id: 's10', load: 0.0007, reading: 0.0007002, direction: 'increasing', repeatNumber: 1, position: 'front-right' },
      { id: 's11', load: 0.0007, reading: 0.0007001, direction: 'increasing', repeatNumber: 1, position: 'back-left' },
      { id: 's12', load: 0.0007, reading: 0.0007002, direction: 'increasing', repeatNumber: 1, position: 'back-right' },
    ],
  },
  {
    id: 'avery-weighbridge',
    name: 'Avery Weigh-Tronix BridgeScale (Class IIII Heavy)',
    classTag: 'Class IIII · 50,000 kg',
    instrument: {
      manufacturer: 'Avery Weigh-Tronix India Ltd.',
      model: 'BMS-T Pitless Heavy Weighbridge',
      serialNumber: 'AWT-WB-50T-2026-88',
      typeApprovalNo: 'IND/LM/WB/2026/0881',
      accuracyClass: 'IIII',
      maxCapacity: 50000.0,
      minCapacity: 400.0,
      verificationScaleIntervalE: 20.0,
      actualScaleIntervalD: 20.0,
      unit: 'kg',
      yearOfManufacture: 2026,
      countryOfOrigin: 'India',
      tareCapacity: 50000.0,
    },
    conditions: {
      temperatureC: 32.5,
      humidityPercent: 62,
      barometricPressureHpa: 1008.0,
      gravityMps2: 9.789,
      referenceMassStandard: 'OIML Class M1 1000kg Heavy Test Blocks with Mobile Crane Rig',
      standardsTraceabilityNo: 'RRSL/FBD/WB/2026/0019',
      testLocation: 'Inland Container Depot (ICD), Tughlakabad',
      inspectorName: 'Vikas Meena',
      inspectorId: 'INS-DL-2023-0145',
      testDate: '2026-09-27',
    },
    readings: [
      { id: 'wb1', load: 0, reading: 0, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 'wb2', load: 10000, reading: 10000, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 'wb3', load: 20000, reading: 20010, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 'wb4', load: 30000, reading: 30010, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 'wb5', load: 40000, reading: 40020, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 'wb6', load: 50000, reading: 50020, direction: 'increasing', repeatNumber: 1, position: 'center' },
      { id: 'wb7', load: 50000, reading: 50020, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      { id: 'wb8', load: 30000, reading: 30010, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      { id: 'wb9', load: 10000, reading: 10000, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      { id: 'wb10', load: 0, reading: 0, direction: 'decreasing', repeatNumber: 1, position: 'center' },
      // Corner tests at 15000 kg
      { id: 'wb11', load: 15000, reading: 15010, direction: 'increasing', repeatNumber: 1, position: 'front-left' },
      { id: 'wb12', load: 15000, reading: 15000, direction: 'increasing', repeatNumber: 1, position: 'front-right' },
      { id: 'wb13', load: 15000, reading: 15010, direction: 'increasing', repeatNumber: 1, position: 'back-left' },
      { id: 'wb14', load: 15000, reading: 15010, direction: 'increasing', repeatNumber: 1, position: 'back-right' },
    ],
  },
];
