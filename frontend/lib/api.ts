"use client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "dd_token";

export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;
  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function handle(res: Response) {
  if (res.status === 401 && typeof window !== "undefined") {
    setToken(null);
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  if (!res.ok) {
    let code = "http_error", message = `Request failed (${res.status})`, details = {};
    try {
      const body = await res.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
        details = body.error.details ?? {};
      } else if (body?.detail) {
        message = typeof body.detail === "string" ? body.detail : message;
      }
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, code, message, details);
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && typeof options.body === "string") headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  return handle(res) as Promise<T>;
}

export async function apiFile(path: string): Promise<Blob> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, { headers });
  if (!res.ok) {
    await handle(res);
    throw new ApiError(res.status, "http_error", `Request failed (${res.status})`);
  }
  return res.blob();
}

export const apiGet = <T = unknown>(path: string) => api<T>(path);
export const apiPost = <T = unknown>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const apiPatch = <T = unknown>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const apiDelete = (path: string) => api<void>(path);

export function fileUrl(documentId: string): string {
  return `${API_URL}/api/documents/${documentId}/file`;
}

export async function uploadFiles(companyId: string, files: File[], params?: { document_type?: string; fiscal_year?: string }): Promise<DocumentItem_inferred[]> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const qs = new URLSearchParams();
  if (params?.document_type) qs.set("document_type", params.document_type);
  if (params?.fiscal_year) qs.set("fiscal_year", params.fiscal_year);
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}/api/companies/${companyId}/documents?${qs}`, {
    method: "POST", headers, body: form,
  });
  return handle(res);
}

type DocumentItem_inferred = import("@/types").DocumentItem;
