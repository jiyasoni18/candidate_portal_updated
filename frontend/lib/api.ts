import type { SessionSummary, SessionDetail, StartSessionResponse } from "@/types/session";
import type { TokenResponse } from "@/types/auth";

const API_BASE = "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("auth_token");
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse<TokenResponse>(res);
}

export async function registerUser(
  fullName: string,
  email: string,
  password: string
): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, email, password }),
  });
  return handleResponse<TokenResponse>(res);
}

export async function fetchSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE}/practice/sessions`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<SessionSummary[]>(res);
}

export async function initializeSession(
  formData: FormData
): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/practice/initialize`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
  return handleResponse<{ session_id: string }>(res);
}

export async function fetchSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/practice/session/${sessionId}`, {
    headers: { ...authHeaders() },
  });
  return handleResponse<SessionDetail>(res);
}

export async function startSession(sessionId: string): Promise<StartSessionResponse> {
  const res = await fetch(`${API_BASE}/practice/session/${sessionId}/start`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  return handleResponse<StartSessionResponse>(res);
}

export async function refineCustomAdditions(
  sessionId: string,
  additions: string
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/practice/session/${sessionId}/refine`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ custom_additions: additions }),
  });
  return handleResponse<{ success: boolean }>(res);
}

export interface RefineResponse {
  session_id: string;
  status: string;
  enhanced_analysis?: Record<string, unknown>;
  refined_gaps?: Record<string, string>;
  refined_custom_items?: string[];
}

export async function refineWithGaps(
  sessionId: string,
  customAdditions: string,
  gapSelections: Record<string, string>,
  selectedImprovements: string[],
  preRefined?: boolean
): Promise<RefineResponse> {
  const res = await fetch(`${API_BASE}/practice/session/${sessionId}/refine`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      custom_additions: customAdditions,
      gap_selections: gapSelections,
      selected_improvements: selectedImprovements,
      ...(preRefined ? { pre_refined: true } : {}),
    }),
  });
  return handleResponse<RefineResponse>(res);
}

export async function generatePDF(
  sessionId: string,
  template?: string
): Promise<Blob> {
  const url = template
    ? `${API_BASE}/practice/session/${sessionId}/pdf?template=${encodeURIComponent(template)}`
    : `${API_BASE}/practice/session/${sessionId}/pdf`;
  const res = await fetch(url, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse errors on error responses
    }
    throw new ApiError(res.status, detail);
  }
  return res.blob();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/practice/session/${sessionId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
}

export async function downloadResume(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/practice/session/${sessionId}/resume`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
  
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.target = "_blank";
  // Attempt to open in a new tab; browser might block if not directly triggered by user click, 
  // but this is called in an onClick handler, so it should be fine.
  a.click();
  window.URL.revokeObjectURL(url);
}
