import { InstrumentProfile, TestConditions, ReadingItem, MetrologyComputation, AuditHistoryRecord } from '../types/metrology';

const API_BASE = typeof window !== 'undefined' && window.location.port === '5173'
  ? 'http://localhost:8000/api'
  : '/api';

export interface BackendStatus {
  online: boolean;
  engine?: string;
  reports_count?: number;
  stats?: {
    total_tests: number;
    pass_rate: number;
    avg_compliance_score: number;
    risk_distribution: Record<string, number>;
  };
}

export async function checkBackendStatus(): Promise<BackendStatus> {
  try {
    const res = await fetch(`${API_BASE}/status`, { method: 'GET', signal: AbortSignal.timeout(2000) });
    if (!res.ok) return { online: false };
    const data = await res.json();
    return { online: true, ...data };
  } catch {
    return { online: false };
  }
}

export async function saveAuditToBackend(
  reportId: string,
  instrument: InstrumentProfile,
  conditions: TestConditions,
  computation: MetrologyComputation
): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${API_BASE}/save_audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report_id: reportId,
        instrument: {
          manufacturer: instrument.manufacturer,
          model: instrument.model,
          serial_number: instrument.serialNumber,
          type_approval_no: instrument.typeApprovalNo,
          max_capacity: instrument.maxCapacity,
          min_capacity: instrument.minCapacity,
          verification_scale_interval_e: instrument.verificationScaleIntervalE,
          accuracy_class: instrument.accuracyClass,
        },
        test_conditions: {
          temperature_c: conditions.temperatureC,
          humidity_percent: conditions.humidityPercent,
          barometric_pressure_hpa: conditions.barometricPressureHpa,
          test_location: conditions.testLocation,
          inspector_name: conditions.inspectorName,
          inspector_id: conditions.inspectorId,
        },
        calculations: {
          combined_uncertainty: computation.combinedUncertainty,
          compliance_score: computation.complianceScore,
          risk_level: computation.riskLevel,
          verification_hash: computation.verificationHash,
        },
        conformity: computation.overallPass,
      }),
    });
    return await res.json();
  } catch (e: any) {
    return { success: false, message: e.message || 'Failed to reach Python backend' };
  }
}

export async function generateReportLabPdf(
  instrument: InstrumentProfile,
  conditions: TestConditions,
  readings: ReadingItem[]
): Promise<{ success: boolean; pdf_url?: string; error?: string; message?: string }> {
  try {
    const res = await fetch(`${API_BASE}/generate_pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instrument,
        test_conditions: conditions,
        readings,
      }),
    });
    return await res.json();
  } catch (e: any) {
    return { success: false, error: e.message || 'Failed to reach backend' };
  }
}

export async function fetchAuditHistory(serialNumber?: string): Promise<AuditHistoryRecord[]> {
  try {
    const url = serialNumber ? `${API_BASE}/history?serial=${encodeURIComponent(serialNumber)}` : `${API_BASE}/history`;
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}
