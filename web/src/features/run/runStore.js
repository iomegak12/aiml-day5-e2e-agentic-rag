// Live runs outlive the page that started them: the stream started on "New chat" keeps feeding the
// Live run screen after navigation, and "Stop watching" + resume re-attaches with Last-Event-ID.
import { useCallback, useSyncExternalStore } from 'react';
import { paths } from '../../api/endpoints';
import { queryClient } from '../../api/queryClient';
import { openStream } from '../../api/sse';
import { eventTimeMs } from '../../lib/format';
import { initialRunState, runReducer } from './runReducer';

/** @type {Map<string, {state: object, controller: AbortController|null}>} */
const entries = new Map();
/** @type {Map<string, Set<() => void>>} */
const listeners = new Map();

function emit(id) {
  listeners.get(id)?.forEach((fn) => fn());
}

function dispatch(id, action) {
  const entry = entries.get(id);
  if (!entry) return;
  entry.state = runReducer(entry.state, action);
  emit(id);
  if (action.type === 'event' && action.event.event === 'done') {
    queryClient.invalidateQueries({ queryKey: ['requests'] });
    queryClient.invalidateQueries({ queryKey: ['request', id] });
  }
}

function ensure(id, extra) {
  if (!entries.has(id)) entries.set(id, { state: initialRunState(id, extra), controller: null });
  return entries.get(id);
}

function settle(id, controller, error) {
  const entry = entries.get(id);
  if (!entry || entry.controller !== controller) return; // a newer connection owns the entry
  entry.controller = null;
  dispatch(id, error ? { type: 'connection-error', error } : { type: 'closed' });
}

export const getRun = (id) => entries.get(id)?.state ?? null;

export function subscribeRun(id, fn) {
  if (!listeners.has(id)) listeners.set(id, new Set());
  listeners.get(id).add(fn);
  return () => listeners.get(id)?.delete(fn);
}

export const isAttached = (id) => Boolean(entries.get(id)?.controller);

/**
 * POST /ask/stream. Resolves with the request_id from the first `accepted` event; the stream keeps
 * running in the background. Rejects with ApiError (429, 422, 503, ...) when the run was not accepted.
 */
export function startAsk(body) {
  const controller = new AbortController();
  let id = null;
  return new Promise((resolve, reject) => {
    openStream({
      url: paths.askStream,
      method: 'POST',
      body,
      signal: controller.signal,
      onEvent(ev) {
        if (!id && ev.event === 'accepted') {
          id = ev.data.request_id;
          const entry = ensure(id, { question: body.question, mode: body.mode });
          entry.controller = controller;
          dispatch(id, { type: 'connecting' });
          resolve(id);
        }
        if (id) dispatch(id, { type: 'event', event: ev });
      },
    })
      .then(() =>
        id ? settle(id, controller) : reject(new Error('The stream closed before it was accepted.')),
      )
      .catch((err) => (id ? settle(id, controller, err) : reject(err)));
  });
}

/**
 * GET /requests/{id}/events. A fresh attach replays every buffered event; a resume sends Last-Event-ID
 * and marks the events that happened while we were away as `replayed`.
 */
export function attach(id) {
  const entry = ensure(id);
  if (entry.controller || entry.state.phase === 'done') return;
  const resuming = entry.state.events.length > 0;
  const last = entry.state.lastEventId;
  const lastEventId = last && !last.startsWith('db-') ? last : undefined;
  const controller = new AbortController();
  entry.controller = controller;
  const attachedAt = Date.now();
  dispatch(id, { type: 'connecting', resuming });
  openStream({
    url: paths.events(id),
    lastEventId,
    signal: controller.signal,
    onEvent(ev) {
      const ms = eventTimeMs(ev.id);
      dispatch(id, { type: 'event', event: ev, replayed: resuming && (ms === null || ms < attachedAt) });
    },
  })
    .then(() => settle(id, controller))
    .catch((err) => settle(id, controller, err));
}

/** "Stop watching": close our connection; the run continues on the server. */
export function detach(id) {
  const entry = entries.get(id);
  if (!entry) return;
  entry.controller?.abort();
  entry.controller = null;
  dispatch(id, { type: 'detach' });
}

/** Sign-out: drop every connection and cached run. */
export function resetRuns() {
  for (const entry of entries.values()) entry.controller?.abort();
  entries.clear();
  listeners.forEach((set) => set.forEach((fn) => fn()));
}

/** React hook: the live state of one run (null until it is started or attached). */
export function useRun(id) {
  const subscribe = useCallback((fn) => subscribeRun(id, fn), [id]);
  return useSyncExternalStore(subscribe, () => getRun(id));
}
