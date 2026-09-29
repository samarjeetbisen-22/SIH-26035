import { InstrumentProfile, TestConditions, ReadingItem, MetrologyComputation, AuditHistoryRecord } from '../types/metrology';

export const API_BASE = typeof window !== 'undefined' && window.location.port === '5173'
  ? 'http://localhost:8000/api'
  : '/api';

export interface UserSession {
  id: string;
  username: string;
  full_name: string;
  role: 'ADMIN' | 'INSPECTOR' | 'REVIEWER' | 'OWNER';
  organization?: string;
  badge_id?: string;
}

export function getAuthToken(): string | null {
  return localStorage.getItem('metrolab_token');
}

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem('metrolab_token', token);
  } else {
    localStorage.removeItem('metrolab_token');
  }
}

export function getAuthUser(): UserSession | null {
  const raw = localStorage.getItem('metrolab_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAuthUser(user: UserSession | null) {
  if (user) {
    localStorage.setItem('metrolab_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('metrolab_user');
  }
}

export async function loginUser(username: string, password: string): Promise<{ success: boolean; token?: string; user?: UserSession; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok && data.token) {
      setAuthToken(data.token);
      setAuthUser(data.user);
      return { success: true, token: data.token, user: data.user };
    }
    return { success: false, error: data.error || 'Login failed' };
  } catch (err: any) {
    return { success: false, error: err.message || 'Connection refused' };
  }
}

export async function logoutUser() {
  const token = getAuthToken();
  if (token) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
    } catch {}
  }
  setAuthToken(null);
  setAuthUser(null);
}

export async function validateSession(): Promise<UserSession | null> {
  const token = getAuthToken();
  if (!token) {
    setAuthUser(null);
    return null;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.user) {
        setAuthUser(data.user);
        return data.user;
      }
    }
  } catch (err) {
    console.error("Session verification error:", err);
  }
  // Token expired or invalid
  setAuthToken(null);
  setAuthUser(null);
  return null;
}

export async function checkBackendStatus() {
  try {
    const res = await fetch(`${API_BASE}/status`, { signal: AbortSignal.timeout(2500) });
    if (!res.ok) return { online: false };
    const data = await res.json();
    return { online: true, ...data };
  } catch {
    return { online: false };
  }
}

export async function fetchDashboardStats() {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/dashboard/stats`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchInstruments() {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/instruments`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.instruments || [];
  } catch {
    return [];
  }
}

export async function fetchEvaluations(status?: string) {
  const token = getAuthToken();
  try {
    const url = status ? `${API_BASE}/evaluations?status=${encodeURIComponent(status)}` : `${API_BASE}/evaluations`;
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.evaluations || [];
  } catch {
    return [];
  }
}

export async function fetchEvaluationDetails(evalId: string) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function createEvaluation(payload: any) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(payload)
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function saveReadingsToEvaluation(evalId: string, readings: any[]) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}/readings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ readings })
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function submitForReview(evalId: string) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function updateEvaluation(evalId: string, payload: any) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(payload)
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function deleteEvaluation(evalId: string) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}`, {
      method: 'DELETE',
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function reviewEvaluation(evalId: string, verdict: 'APPROVE' | 'REJECT' | 'RETURN' | 'UNDER_REVIEW', comments: string = '') {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ verdict, comments })
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function uploadEvaluationAttachment(evalId: string, fileDataB64: string, filename: string, description: string, mimeType: string) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}/attachments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        filename,
        file_data: fileDataB64,
        description,
        mime_type: mimeType
      })
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function generateEvaluationPdf(evalId: string) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}/generate_pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    });
    return await res.json();
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function fetchEvaluationReport(evalId: string) {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/evaluations/${evalId}/report`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchReports(filters?: { evaluation_id?: string; instrument_id?: string; serial?: string }) {
  const token = getAuthToken();
  try {
    const params = new URLSearchParams();
    if (filters?.evaluation_id) params.append('evaluation_id', filters.evaluation_id);
    if (filters?.instrument_id) params.append('instrument_id', filters.instrument_id);
    if (filters?.serial) params.append('serial', filters.serial);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/reports${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.reports || [];
  } catch {
    return [];
  }
}

export async function fetchAuditLogs() {
  const token = getAuthToken();
  try {
    const res = await fetch(`${API_BASE}/audit`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.audit_logs || data.logs || [];
  } catch {
    return [];
  }
}

// Legacy wrappers for standalone compatibility
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
        instrument,
        test_conditions: conditions,
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
  const token = getAuthToken();
  try {
    const url = serialNumber ? `${API_BASE}/history?serial=${encodeURIComponent(serialNumber)}` : `${API_BASE}/history`;
    const res = await fetch(url, {
      signal: AbortSignal.timeout(3000),
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.history || [];
  } catch {
    return [];
  }
}
