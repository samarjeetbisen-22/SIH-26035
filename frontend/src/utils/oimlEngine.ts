import {
  AccuracyClass,
  InstrumentProfile,
  ReadingItem,
  PointResult,
  EccentricityResult,
  RepeatabilityResult,
  MetrologyComputation,
  PlatformPosition
} from '../types/metrology';

export interface MpeTier {
  min_e: number;
  max_e: number;
  mpeFactor: number;
}

export const OIML_LIMITS: Record<AccuracyClass, MpeTier[]> = {
  I: [
    { min_e: 0, max_e: 50000, mpeFactor: 0.5 },
    { min_e: 50000, max_e: 200000, mpeFactor: 1.0 },
    { min_e: 200000, max_e: Infinity, mpeFactor: 1.5 },
  ],
  II: [
    { min_e: 0, max_e: 5000, mpeFactor: 0.5 },
    { min_e: 5000, max_e: 20000, mpeFactor: 1.0 },
    { min_e: 20000, max_e: 100000, mpeFactor: 1.5 },
  ],
  III: [
    { min_e: 0, max_e: 500, mpeFactor: 0.5 },
    { min_e: 500, max_e: 2000, mpeFactor: 1.0 },
    { min_e: 2000, max_e: 10000, mpeFactor: 1.5 },
  ],
  IIII: [
    { min_e: 0, max_e: 50, mpeFactor: 0.5 },
    { min_e: 50, max_e: 200, mpeFactor: 1.0 },
    { min_e: 200, max_e: 1000, mpeFactor: 1.5 },
  ],
};

/**
 * Computes OIML Maximum Permissible Error (MPE) for a given load and verification scale interval e.
 */
export function calculateMpe(load: number, e: number, accuracyClass: AccuracyClass): number {
  if (e <= 0) return 0;
  const loadE = Math.abs(load) / e;
  const tiers = OIML_LIMITS[accuracyClass] || OIML_LIMITS['III'];
  
  for (const tier of tiers) {
    if (loadE >= tier.min_e && loadE <= tier.max_e) {
      return tier.mpeFactor * e;
    }
  }
  return (tiers[tiers.length - 1]?.mpeFactor ?? 1.5) * e;
}

/**
 * Core Metrological Calculation Engine based on OIML R 76-1
 */
export function computeMetrology(
  instrument: InstrumentProfile,
  readings: ReadingItem[]
): MetrologyComputation {
  const capacity = instrument.maxCapacity || 1.0;
  const e = instrument.verificationScaleIntervalE || 0.001;
  const accClass = instrument.accuracyClass || 'III';
  const scaleIntervalsN = Math.round(capacity / (e || 0.001));

  // 1. Group readings by load
  const groupedByLoad: Record<number, ReadingItem[]> = {};
  for (const r of readings) {
    if (!groupedByLoad[r.load]) {
      groupedByLoad[r.load] = [];
    }
    groupedByLoad[r.load].push(r);
  }

  // 2. Repeatability Calculation
  let maxRepeatabilityErr = 0;
  const repeatabilitySummaries: RepeatabilityResult[] = [];

  for (const [loadStr, rList] of Object.entries(groupedByLoad)) {
    const load = parseFloat(loadStr);
    const centerInc = rList.filter(
      r => r.direction === 'increasing' && (r.position === 'center' || !r.position)
    );

    if (centerInc.length >= 2) {
      const vals = centerInc.map(r => r.reading);
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      const variance =
        vals.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (vals.length - 1);
      const stdev = Math.sqrt(variance);
      const range = Math.max(...vals) - Math.min(...vals);
      const mpe = calculateMpe(load, e, accClass);
      
      const err = stdev / capacity;
      if (err > maxRepeatabilityErr) {
        maxRepeatabilityErr = err;
      }

      repeatabilitySummaries.push({
        load,
        runs: centerInc.map(r => ({
          runIndex: r.repeatNumber,
          reading: r.reading,
          error: Number((r.reading - r.load).toFixed(5)),
        })),
        mean: Number(mean.toFixed(5)),
        standardDeviation: Number(stdev.toFixed(6)),
        maxRange: Number(range.toFixed(5)),
        mpe: Number(mpe.toFixed(5)),
        passed: range <= mpe, // OIML R 76-1: Difference between max and min shall not exceed MPE
      });
    }
  }

  const repeatability = maxRepeatabilityErr > 0 ? maxRepeatabilityErr : 0.0001;

  // 3. Linearity Calculation (Maximum indication deviation relative to capacity)
  let linearity = 0;
  for (const r of readings) {
    const dev = Math.abs(r.reading - r.load) / capacity;
    if (dev > linearity) {
      linearity = dev;
    }
  }

  // 4. Hysteresis Calculation (Difference between increasing and decreasing cycles)
  let hysteresis = 0;
  for (const [, rList] of Object.entries(groupedByLoad)) {
    const inc = rList.filter(r => r.direction === 'increasing').map(r => r.reading);
    const dec = rList.filter(r => r.direction === 'decreasing').map(r => r.reading);
    if (inc.length > 0 && dec.length > 0) {
      const avgInc = inc.reduce((a, b) => a + b, 0) / inc.length;
      const avgDec = dec.reduce((a, b) => a + b, 0) / dec.length;
      const diff = Math.abs(avgInc - avgDec) / capacity;
      if (diff > hysteresis) {
        hysteresis = diff;
      }
    }
  }

  // 5. Eccentricity (Corner Load) Calculation
  let eccentricity = 0;
  const eccentricityReadingsMap: Record<PlatformPosition, { reading: number; error: number; mpe: number; passed: boolean }> = {
    center: { reading: 0, error: 0, mpe: 0, passed: true },
    'front-left': { reading: 0, error: 0, mpe: 0, passed: true },
    'front-right': { reading: 0, error: 0, mpe: 0, passed: true },
    'back-left': { reading: 0, error: 0, mpe: 0, passed: true },
    'back-right': { reading: 0, error: 0, mpe: 0, passed: true },
  };

  let eccTestLoad = capacity / 3;
  let hasEccReadings = false;

  for (const [loadStr, rList] of Object.entries(groupedByLoad)) {
    const positions: Partial<Record<PlatformPosition, number[]>> = {};
    for (const r of rList) {
      const pos = r.position || 'center';
      if (!positions[pos]) positions[pos] = [];
      positions[pos]!.push(r.reading);
    }

    const uniquePositions = Object.keys(positions);
    if (uniquePositions.length > 1) {
      eccTestLoad = parseFloat(loadStr);
      hasEccReadings = true;
      const mpeAtEcc = calculateMpe(eccTestLoad, e, accClass);

      const means: Record<string, number> = {};
      for (const [pos, vals] of Object.entries(positions)) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
        means[pos] = avg;
        const err = avg - eccTestLoad;
        eccentricityReadingsMap[pos as PlatformPosition] = {
          reading: Number(avg.toFixed(5)),
          error: Number(err.toFixed(5)),
          mpe: Number(mpeAtEcc.toFixed(5)),
          passed: Math.abs(err) <= mpeAtEcc,
        };
      }

      const meanVals = Object.values(means);
      const diff = (Math.max(...meanVals) - Math.min(...meanVals)) / capacity;
      if (diff > eccentricity) {
        eccentricity = diff;
      }
    }
  }

  const eccentricitySummary: EccentricityResult = {
    testLoad: Number(eccTestLoad.toFixed(3)),
    readings: (['center', 'front-left', 'front-right', 'back-left', 'back-right'] as PlatformPosition[]).map(pos => ({
      position: pos,
      label: pos.replace('-', ' ').toUpperCase(),
      reading: eccentricityReadingsMap[pos].reading || (hasEccReadings ? eccTestLoad : 0),
      error: eccentricityReadingsMap[pos].error,
      mpe: eccentricityReadingsMap[pos].mpe || calculateMpe(eccTestLoad, e, accClass),
      passed: eccentricityReadingsMap[pos].passed,
    })),
    maxDeviation: Number((eccentricity * capacity).toFixed(5)),
    passed: (eccentricity * capacity) <= calculateMpe(eccTestLoad, e, accClass),
  };

  // 6. Combined Uncertainty (ISO/IEC 17025 & OIML R 76 Guide)
  const combinedUncertainty = Math.sqrt(
    Math.pow(repeatability, 2) +
    Math.pow(linearity, 2) +
    Math.pow(eccentricity, 2) +
    Math.pow(hysteresis, 2)
  );
  const expandedUncertainty = combinedUncertainty * 2.0; // k=2 (95% confidence)

  // 7. Per-Point Load Evaluation
  let overallPass = true;
  const pointResults: PointResult[] = [];

  for (const r of readings) {
    const mpe = calculateMpe(r.load, e, accClass);
    const error = r.reading - r.load;
    const passed = Math.abs(error) <= mpe + 1e-9;
    if (!passed) {
      overallPass = false;
    }

    const ratio = mpe > 0 ? Math.abs(error) / mpe : 0;

    pointResults.push({
      load: Number(r.load.toFixed(4)),
      reading: Number(r.reading.toFixed(4)),
      direction: r.direction,
      error: Number(error.toFixed(5)),
      mpe: Number(mpe.toFixed(5)),
      ratio: Number(ratio.toFixed(3)),
      passed,
      position: r.position,
      repeatNumber: r.repeatNumber,
    });
  }

  if (!eccentricitySummary.passed) {
    overallPass = false;
  }
  for (const rep of repeatabilitySummaries) {
    if (!rep.passed) overallPass = false;
  }

  // 8. Compliance Score (0 - 100%)
  let complianceScore = 100.0;
  if (pointResults.length > 0) {
    const ratios = pointResults.map(p => p.ratio);
    const avgRatio = ratios.reduce((a, b) => a + b, 0) / ratios.length;
    const worstRatio = Math.max(...ratios);
    const blendedRatio = 0.7 * avgRatio + 0.3 * worstRatio;
    complianceScore = Math.max(0.0, Math.min(100.0, 100.0 * (1.0 - blendedRatio)));
  }

  let riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW';
  if (complianceScore >= 90) riskLevel = 'LOW';
  else if (complianceScore >= 70) riskLevel = 'MEDIUM';
  else if (complianceScore >= 50) riskLevel = 'HIGH';
  else riskLevel = 'CRITICAL';

  if (!overallPass && (riskLevel === 'LOW' || riskLevel === 'MEDIUM')) {
    riskLevel = 'HIGH';
  }

  // 9. Generate Deterministic Verification Hash
  const hashSeed = `${instrument.serialNumber}-${instrument.model}-${capacity}-${accClass}-${pointResults.length}-${overallPass ? 'P' : 'F'}`;
  let hashVal = 0;
  for (let i = 0; i < hashSeed.length; i++) {
    hashVal = ((hashVal << 5) - hashVal) + hashSeed.charCodeAt(i);
    hashVal |= 0;
  }
  const hexPart = Math.abs(hashVal).toString(16).padStart(8, '0').toUpperCase();
  const verificationHash = `OIML-R76-2026-${hexPart}-${instrument.serialNumber.replace(/[^A-Za-z0-9]/g, '').slice(-4)}`;

  return {
    repeatabilityError: Number(repeatability.toFixed(7)),
    linearityError: Number(linearity.toFixed(7)),
    hysteresisError: Number(hysteresis.toFixed(7)),
    eccentricityError: Number(eccentricity.toFixed(7)),
    combinedUncertainty: Number(combinedUncertainty.toFixed(7)),
    expandedUncertainty: Number(expandedUncertainty.toFixed(7)),
    pointResults,
    eccentricitySummary,
    repeatabilitySummary: repeatabilitySummaries,
    overallPass,
    complianceScore: Number(complianceScore.toFixed(2)),
    riskLevel,
    verificationHash,
    scaleIntervalsN,
  };
}
