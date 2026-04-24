/**
 * HomeView API client — typed wrappers for all server REST endpoints.
 *
 * The client accepts a bearer token as a parameter or reads it from the
 * context layer (see AppContext). It does not persist tokens itself.
 */

import {
  ApiError,
  CellStatus,
  Layout,
  PairCodeResponse,
  Preset,
  ServerStatus,
  Source,
} from "./types";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function request<T>(
  url: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let code = "HTTP_ERROR";
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      // non-JSON body — keep defaults
    }
    throw new ApiError(code, message);
  }

  // 204 No Content — return empty object
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public endpoints (no auth token attached)
// ---------------------------------------------------------------------------

export async function getPairCode(): Promise<PairCodeResponse> {
  return request<PairCodeResponse>("/api/v1/pair/code");
}

export async function pair(code: string): Promise<string> {
  const result = await request<{ token: string }>("/api/v1/pair", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
  return result.token;
}

// ---------------------------------------------------------------------------
// Protected endpoints (token required)
// ---------------------------------------------------------------------------

export async function getStatus(token: string): Promise<ServerStatus> {
  return request<ServerStatus>("/api/v1/status", {}, token);
}

export async function getSources(token: string): Promise<Source[]> {
  return request<Source[]>("/api/v1/sources", {}, token);
}

export async function assignSource(
  cellIndex: number,
  sourceId: string,
  token: string
): Promise<CellStatus> {
  return request(
    `/api/v1/cells/${cellIndex}/source`,
    { method: "PUT", body: JSON.stringify({ source_id: sourceId }) },
    token
  );
}

export async function clearCell(
  cellIndex: number,
  token: string
): Promise<void> {
  await request(`/api/v1/cells/${cellIndex}/source`, { method: "DELETE" }, token);
}

export async function setLayout(
  layoutId: string,
  token: string
): Promise<void> {
  await request(
    "/api/v1/layout",
    { method: "PUT", body: JSON.stringify({ layout_id: layoutId }) },
    token
  );
}

export async function getLayouts(token: string): Promise<Layout[]> {
  return request<Layout[]>("/api/v1/layouts", {}, token);
}

export async function setActiveAudio(
  cellIndex: number,
  token: string
): Promise<void> {
  await request(
    "/api/v1/audio/active",
    { method: "PUT", body: JSON.stringify({ cell_index: cellIndex }) },
    token
  );
}

export async function getPresets(token: string): Promise<Preset[]> {
  return request<Preset[]>("/api/v1/presets", {}, token);
}

export async function savePreset(name: string, token: string): Promise<Preset> {
  return request<Preset>(
    "/api/v1/presets",
    { method: "POST", body: JSON.stringify({ name }) },
    token
  );
}

export async function applyPreset(
  presetId: string,
  token: string
): Promise<void> {
  await request(`/api/v1/presets/${presetId}/apply`, { method: "PUT" }, token);
}

export async function deletePreset(
  presetId: string,
  token: string
): Promise<void> {
  await request(`/api/v1/presets/${presetId}`, { method: "DELETE" }, token);
}

export async function startInteractive(
  cellIndex: number,
  token: string
): Promise<void> {
  await request(
    "/api/v1/interactive/start",
    { method: "POST", body: JSON.stringify({ cell_index: cellIndex }) },
    token
  );
}

export async function stopInteractive(token: string): Promise<void> {
  await request("/api/v1/interactive/stop", { method: "POST" }, token);
}

// Re-export types for consumer convenience
export type { CellStatus, ApiError } from "./types";
