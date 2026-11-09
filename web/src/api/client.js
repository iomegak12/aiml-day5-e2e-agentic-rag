import { ApiError } from './ApiError';
import { getApiKey } from '../lib/storage';

// The AuthProvider registers a handler so any 401 signs the user out (no import cycle with React code).
let unauthorizedHandler = null;

export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn;
  return () => {
    if (unauthorizedHandler === fn) unauthorizedHandler = null;
  };
}

export function notifyUnauthorized(error) {
  unauthorizedHandler?.(error);
}

/** Headers for an API call: the X-API-Key comes from sessionStorage unless one is passed explicitly. */
export function authHeaders(apiKey) {
  const key = apiKey ?? getApiKey();
  return key ? { 'X-API-Key': key } : {};
}

/**
 * fetch() wrapper for the same-origin API (Nginx in containers, the Vite proxy in dev).
 * Throws ApiError for non-2xx responses (parsed from application/problem+json).
 * @param {string} path  e.g. "/api/v1/me"
 * @param {{method?: string, body?: unknown, signal?: AbortSignal, auth?: boolean, apiKey?: string}} [opts]
 */
export async function apiFetch(path, { method = 'GET', body, signal, auth = true, apiKey } = {}) {
  const headers = { Accept: 'application/json', ...(auth ? authHeaders(apiKey) : {}) };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let res;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause;
    throw ApiError.network(cause);
  }
  if (!res.ok) {
    const error = await ApiError.fromResponse(res);
    // An explicit apiKey is a sign-in attempt: report the 401 to the form instead of signing out.
    if (error.status === 401 && auth && apiKey === undefined) notifyUnauthorized(error);
    throw error;
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('json') ? res.json() : res.text();
}
