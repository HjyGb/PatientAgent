/** API client — thin wrapper around fetch for PatientAgent backend.

 * Phase 3: Attaches JWT Bearer token from auth store when available.
 */

import { getAuthToken } from '../stores/auth-store';

const API_BASE = '/api/v1';

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ── Auth ──
  quickLogin: (employeeId: string) =>
    request<{ access_token: string; user: any }>('/auth/quick-login', {
      method: 'POST',
      body: JSON.stringify({ employee_id: employeeId }),
    }),

  // ── Cases ──
  listCases: (params: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString();
    return request<any>(`/cases?${qs}`);
  },

  loadCase: (caseId: number) =>
    request<{ session_id: string; case_id: number; department: string; chief_complaint: string }>(
      `/cases/${caseId}/load`,
      { method: 'POST' }
    ),

  getCaseDetail: (caseId: number) => request<any>(`/cases/${caseId}`),

  getDepartments: () => request<{ departments: string[] }>('/departments'),

  // ── Chat ──
  sendMessage: (sessionId: string, question: string) =>
    request<{ answer: string; scores: any; turn: number; is_max_turns: boolean }>(
      `/sessions/${sessionId}/messages`,
      { method: 'POST', body: JSON.stringify({ question }) }
    ),

  // SSE streaming URL builder (not a fetch call — used by EventSource)
  // Note: EventSource doesn't support custom headers, so we can't pass JWT.
  // The backend's soft-auth mode handles this gracefully.
  streamUrl: (sessionId: string, question: string) =>
    `${API_BASE}/sessions/${sessionId}/messages/stream?question=${encodeURIComponent(question)}`,

  // ── Session ──
  getSessionInfo: (sessionId: string) => request<any>(`/sessions/${sessionId}/info`),

  endSession: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/end`, { method: 'POST' }),

  getSessionHistory: (page = 1, pageSize = 20) =>
    request<any>(`/sessions/history?page=${page}&page_size=${pageSize}`),

  // ── Evaluation ──
  submitDiagnosis: (sessionId: string, body: any) =>
    request<{ evaluation_id: string }>(`/sessions/${sessionId}/diagnosis`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getEvaluation: (sessionId: string) => request<any>(`/sessions/${sessionId}/evaluation`),
};
