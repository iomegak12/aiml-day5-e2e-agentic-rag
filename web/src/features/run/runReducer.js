// Pure reducer over the agent's SSE events (POST /ask/stream and GET /requests/{id}/events):
// accepted -> plan -> step -> tool_call / trace -> judge -> result | error -> done

/** @typedef {{id: string|null, event: string, data: any}} SseEvent */

export const TERMINAL_STATUSES = new Set(['completed', 'failed', 'timeout', 'client_disconnected']);

export function initialRunState(requestId = null, extra = {}) {
  return {
    requestId,
    phase: 'idle', // idle | connecting | streaming | detached | done | error
    question: null,
    mode: null,
    user: null,
    options: null,
    plans: [], // [{version, label, rationale, steps}]
    steps: {}, // "version:id" -> latest step record
    toolCalls: [],
    trace: [],
    judge: [],
    result: null, // AskResponse
    problem: null, // RFC 9457 problem from an `error` event
    finalStatus: null, // status from `done`
    events: [], // [{id, event, data, replayed}]
    seen: {}, // event ids already applied (resume may overlap)
    lastEventId: null,
    connectionError: null,
    resuming: false,
    replayedCount: 0,
    ...extra,
  };
}

const stepKey = (s) => `${s.version ?? 1}:${s.id}`;

function applyEvent(state, { event, data }) {
  switch (event) {
    case 'accepted':
      return {
        ...state,
        requestId: data.request_id ?? state.requestId,
        user: data.user ?? state.user,
        options: data.options ?? state.options,
        mode: data.options?.mode ?? state.mode,
      };
    case 'plan': {
      const steps = { ...state.steps };
      for (const s of data.steps || []) steps[stepKey(s)] = { ...s, ...steps[stepKey(s)] };
      const plans = [...state.plans.filter((p) => p.version !== data.version), data].sort(
        (a, b) => a.version - b.version,
      );
      return { ...state, plans, steps };
    }
    case 'step':
      return {
        ...state,
        steps: { ...state.steps, [stepKey(data)]: { ...state.steps[stepKey(data)], ...data } },
      };
    case 'tool_call':
      return { ...state, toolCalls: [...state.toolCalls, data] };
    case 'trace':
      return { ...state, trace: [...state.trace, data] };
    case 'judge':
      return { ...state, judge: [...state.judge, data] };
    case 'result':
      return {
        ...state,
        result: data,
        question: data.question ?? state.question,
        mode: data.mode ?? state.mode,
      };
    case 'error':
      return { ...state, problem: data };
    case 'done':
      return { ...state, finalStatus: data.status, phase: 'done' };
    default:
      return state;
  }
}

export function runReducer(state, action) {
  switch (action.type) {
    case 'connecting':
      return {
        ...state,
        phase: state.phase === 'done' ? 'done' : 'connecting',
        connectionError: null,
        resuming: Boolean(action.resuming),
        replayedCount: 0,
      };
    case 'event': {
      const ev = action.event;
      if (ev.id && state.seen[ev.id]) return state;
      const replayed = Boolean(action.replayed);
      const next = {
        ...state,
        events: [...state.events, { ...ev, replayed }],
        seen: ev.id ? { ...state.seen, [ev.id]: true } : state.seen,
        lastEventId: ev.id ?? state.lastEventId,
        phase: state.phase === 'connecting' || state.phase === 'idle' ? 'streaming' : state.phase,
        replayedCount: state.replayedCount + (replayed ? 1 : 0),
      };
      return applyEvent(next, ev);
    }
    case 'closed':
      return { ...state, phase: state.finalStatus ? 'done' : 'detached' };
    case 'detach':
      return { ...state, phase: state.phase === 'done' ? 'done' : 'detached' };
    case 'connection-error':
      return { ...state, phase: state.finalStatus ? 'done' : 'error', connectionError: action.error };
    default:
      return state;
  }
}

/** Steps of one plan version, merged with their latest status from `step` events. */
export function planSteps(state, version) {
  const plan = state.plans.find((p) => p.version === version);
  return (plan?.steps || []).map((s) => state.steps[stepKey(s)] || s);
}

export const latestPlan = (state) => state.plans[state.plans.length - 1] || null;
