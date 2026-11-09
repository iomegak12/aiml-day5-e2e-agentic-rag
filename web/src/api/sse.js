import { EventStreamContentType, fetchEventSource } from '@microsoft/fetch-event-source';
import { ApiError } from './ApiError';
import { authHeaders, notifyUnauthorized } from './client';

/**
 * Open an SSE stream with fetch (native EventSource cannot POST or send X-API-Key).
 * No automatic retry: re-POSTing /ask/stream would start a second run. Resume is explicit,
 * via GET /requests/{id}/events with Last-Event-ID (see features/run/runStore.js).
 *
 * Resolves with {finished, aborted} when the server closes the stream or the signal aborts;
 * rejects with ApiError when the response is not a 2xx event stream or the connection fails.
 */
export function openStream({ url, method = 'GET', body, lastEventId, signal, onEvent }) {
  const headers = { Accept: EventStreamContentType, ...authHeaders() };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (lastEventId) headers['Last-Event-ID'] = lastEventId;
  let finished = false;

  return fetchEventSource(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
    openWhenHidden: true, // never close and re-open (re-POST) when the tab is hidden
    async onopen(res) {
      const ct = res.headers.get('content-type') || '';
      if (res.ok && ct.startsWith(EventStreamContentType)) return;
      const error = res.ok
        ? new ApiError(
            { title: 'Unexpected response', detail: `Expected an event stream, got "${ct}"` },
            { status: res.status },
          )
        : await ApiError.fromResponse(res);
      if (error.status === 401) notifyUnauthorized(error);
      throw error;
    },
    onmessage(msg) {
      if (!msg.event) return; // keep-alive pings
      let data = msg.data;
      try {
        data = JSON.parse(msg.data);
      } catch {
        /* plain-text payload */
      }
      if (msg.event === 'done') finished = true;
      onEvent({ id: msg.id || null, event: msg.event, data });
    },
    onclose() {
      /* returning (not throwing) ends the stream without a retry */
    },
    onerror(err) {
      throw err instanceof ApiError ? err : ApiError.network(err);
    },
  }).then(() => ({ finished, aborted: Boolean(signal?.aborted) }));
}
