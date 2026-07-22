/**
 * API Client — typed fetch wrapper for the AetherOS backend.
 *
 * Port of apps/web/src/lib/api.ts adapted for React Native:
 *  - Uses expo-secure-store instead of localStorage
 *  - Automatic 401 → refresh → retry interceptor
 *  - SSE stream reader for chat and reading endpoints
 *  - Configurable base URL (dev: LAN IP, prod: real domain)
 */

import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './secure-storage';
import Constants from 'expo-constants';

// ── Base URL resolution ─────────────────────────────────────────────────────

function resolveBaseUrl(): string {
  // Allow override via Expo config
  const configUrl = Constants.expoConfig?.extra?.apiBaseUrl;
  if (configUrl) return configUrl;
  // Default to local dev server
  return 'http://localhost:8000';
}

export const API_BASE_URL = resolveBaseUrl();

// ── Types ───────────────────────────────────────────────────────────────────

interface FetchOptions extends Omit<RequestInit, 'body'> {
  json?: unknown;
  body?: BodyInit;
}

export interface SSEEvent {
  data: string;
}

// ── Token refresh lock (prevents concurrent refresh races) ──────────────────

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  const refresh = await getRefreshToken();
  if (!refresh) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    await setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// ── Core fetch ──────────────────────────────────────────────────────────────

export async function apiFetch<T = unknown>(path: string, options: FetchOptions = {}): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(options.headers as HeadersInit | undefined);

  // Bypass Cloudflare quick tunnel warning page
  headers.set('bypass-tunnel-warning', 'true');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (options.json && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
    options.body = JSON.stringify(options.json);
  }

  const url = `${API_BASE_URL}${path}`;
  console.log(`[apiFetch] Requesting: ${url}`, { method: options.method || 'GET', json: options.json });
  
  let response: Response;
  try {
    response = await fetch(url, { ...options, headers, body: options.body });
    console.log(`[apiFetch] Response received: ${url} (status: ${response.status})`);
  } catch (err) {
    console.error(`[apiFetch] Network/Fetch Error for ${url}:`, err);
    throw err;
  }

  // ── 401 → refresh → retry ──────────────────────────────────────────────
  const skipRefreshPaths = ['/auth/login', '/auth/register', '/auth/refresh'];
  if (response.status === 401 && !skipRefreshPaths.includes(path)) {
    console.log(`[apiFetch] Received 401. Attempting token refresh...`);
    if (!refreshPromise) {
      refreshPromise = attemptTokenRefresh().finally(() => {
        refreshPromise = null;
      });
    }

    const refreshed = await refreshPromise;
    console.log(`[apiFetch] Token refresh outcome: ${refreshed}`);
    if (refreshed) {
      const newToken = await getAccessToken();
      headers.set('Authorization', `Bearer ${newToken}`);
      try {
        response = await fetch(url, { ...options, headers, body: options.body });
        console.log(`[apiFetch] Retry Response received: ${url} (status: ${response.status})`);
      } catch (err) {
        console.error(`[apiFetch] Retry Network/Fetch Error for ${url}:`, err);
        throw err;
      }
    } else {
      await clearTokens();
      throw new AuthExpiredError();
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    console.warn(`[apiFetch] Response not ok: ${url}`, errorData);
    
    let errorMessage = `HTTP ${response.status}`;
    if (errorData && errorData.detail) {
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail
          .map((err: any) => {
            const field = err.loc ? err.loc.filter((l: any) => l !== 'body').join('.') : '';
            return field ? `${field}: ${err.msg}` : err.msg;
          })
          .join('\n');
      }
    }
    
    throw new ApiError(errorMessage, response.status);
  }

  if (response.status === 204) return null as T;
  
  try {
    const parsed = await response.json();
    return parsed as T;
  } catch (err) {
    console.error(`[apiFetch] JSON parsing failed for response from ${url}:`, err);
    throw err;
  }
}

// ── SSE stream reader ───────────────────────────────────────────────────────

export async function* apiStream(path: string, options: FetchOptions = {}): AsyncGenerator<string> {
  const token = await getAccessToken();
  const url = `${API_BASE_URL}${path}`;

  const queue: string[] = [];
  let done = false;
  let error: any = null;
  let resolveNext: (() => void) | null = null;

  const xhr = new XMLHttpRequest();
  xhr.open(options.method || 'GET', url, true);
  
  // Set headers
  xhr.setRequestHeader('bypass-tunnel-warning', 'true');
  xhr.setRequestHeader('Accept', 'text/event-stream');
  if (token) {
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
  }
  
  if (options.headers) {
    const customHeaders = options.headers as Record<string, string>;
    Object.entries(customHeaders).forEach(([k, v]) => {
      xhr.setRequestHeader(k, v);
    });
  }

  if (options.json) {
    xhr.setRequestHeader('Content-Type', 'application/json');
  }

  let offset = 0;

  xhr.onprogress = () => {
    if (xhr.status > 0 && xhr.status >= 400) {
      error = new ApiError(`Stream error: HTTP ${xhr.status}`, xhr.status);
      done = true;
      if (resolveNext) {
        resolveNext();
        resolveNext = null;
      }
      return;
    }

    const text = xhr.responseText;
    const chunk = text.slice(offset);
    offset = text.length;
    
    if (chunk) {
      queue.push(chunk);
      if (resolveNext) {
        resolveNext();
        resolveNext = null;
      }
    }
  };

  xhr.onload = () => {
    if (xhr.status >= 400) {
      error = new ApiError(`Stream error: HTTP ${xhr.status}`, xhr.status);
    }
    done = true;
    if (resolveNext) {
      resolveNext();
      resolveNext = null;
    }
  };

  xhr.onerror = (e) => {
    error = e || new Error('XHR stream error');
    done = true;
    if (resolveNext) {
      resolveNext();
      resolveNext = null;
    }
  };

  const body = options.json ? JSON.stringify(options.json) : (options.body as string | undefined);
  xhr.send(body);

  let buffer = '';

  while (true) {
    if (queue.length === 0 && !done) {
      await new Promise<void>((resolve) => {
        resolveNext = resolve;
      });
    }

    if (error) {
      throw error;
    }

    while (queue.length > 0) {
      const chunk = queue.shift()!;
      buffer += chunk;
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const payload = trimmed.slice(6);
          if (payload === '[DONE]') return;
          try {
            const parsed = JSON.parse(payload);
            if (parsed.content) yield parsed.content;
          } catch {
            yield payload;
          }
        }
      }
    }

    if (done && queue.length === 0) {
      break;
    }
  }
}

// ── Binary download (for PDF export) ────────────────────────────────────────

export async function apiFetchBlob(path: string, options: FetchOptions = {}): Promise<Blob> {
  const token = await getAccessToken();
  const headers = new Headers(options.headers as HeadersInit | undefined);

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (options.json) {
    headers.set('Content-Type', 'application/json');
    options.body = JSON.stringify(options.json);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, body: options.body });
  if (!response.ok) throw new ApiError(`PDF export failed`, response.status);
  return response.blob();
}

// ── Error classes ───────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export class AuthExpiredError extends Error {
  constructor() {
    super('Session expired. Please log in again.');
    this.name = 'AuthExpiredError';
  }
}
