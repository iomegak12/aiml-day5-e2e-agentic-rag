import { apiFetch } from './client';

const BASE = '/api/v1';
const enc = encodeURIComponent;

export const paths = {
  askStream: `${BASE}/agent/ask/stream`,
  events: (id) => `${BASE}/agent/requests/${enc(id)}/events`,
};

/** Every REST call the UI makes (SSE streams are in sse.js and features/run/runStore.js). */
export const api = {
  me: (apiKey) => apiFetch(`${BASE}/me`, { apiKey }),
  listRequests: ({ status, limit = 20, cursor } = {}) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (status) qs.set('status', status);
    if (cursor) qs.set('cursor', cursor);
    return apiFetch(`${BASE}/agent/requests?${qs}`);
  },
  getRequest: (id) => apiFetch(`${BASE}/agent/requests/${enc(id)}`),
  health: () => apiFetch('/health', { auth: false }),
  ready: () => apiFetch('/ready', { auth: false }),
};
