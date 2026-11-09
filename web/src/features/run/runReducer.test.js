import { describe, expect, it } from 'vitest';
import { initialRunState, latestPlan, planSteps, runReducer } from './runReducer';

const step = (id, status, extra = {}) => ({
  id,
  version: 1,
  goal: `goal ${id}`,
  tool: 'search_knowledge_base',
  domains: ['networking'],
  query: `q${id}`,
  depends_on: [],
  status,
  relevant: 0,
  best: 0,
  seconds: 0,
  ...extra,
});

// Same order the API streams them (api/app/services/agent_service.py).
const EVENTS = [
  {
    id: '1000-0',
    event: 'accepted',
    data: {
      request_id: 'r1',
      user: { id: 'bob', role: 'employee' },
      options: { mode: 'plan', timeout_seconds: 120 },
    },
  },
  { id: '1001-0', event: 'trace', data: { t: 0.1, step: 'Request', decision: 'bob', detail: 'q' } },
  {
    id: '1002-0',
    event: 'plan',
    data: {
      version: 1,
      label: 'plan',
      rationale: 'two lookups',
      steps: [step(1, 'pending'), step(2, 'pending')],
    },
  },
  { id: '1003-0', event: 'step', data: step(1, 'running') },
  { id: '1004-0', event: 'step', data: step(1, 'done', { relevant: 3, best: 0.92, seconds: 4.1 }) },
  {
    id: '1005-0',
    event: 'tool_call',
    data: { seq: 1, name: 'search_knowledge_base', origin: 'planner', status: 'ok' },
  },
  {
    id: '1006-0',
    event: 'judge',
    data: { attempt: 1, passed: true, action: 'accept', scores: { faithfulness: 1 } },
  },
  {
    id: '1007-0',
    event: 'result',
    data: {
      request_id: 'r1',
      status: 'completed',
      agent_status: 'answered',
      question: 'Q?',
      mode: 'plan',
      answer: 'A',
    },
  },
  { id: '1008-0', event: 'done', data: { request_id: 'r1', status: 'completed' } },
];

const play = (events, state = initialRunState('r1')) =>
  events.reduce((s, e) => runReducer(s, { type: 'event', event: e }), state);

describe('runReducer', () => {
  it('folds a full plan-mode stream into run state', () => {
    const s = play(EVENTS);
    expect(s.phase).toBe('done');
    expect(s.finalStatus).toBe('completed');
    expect(s.user).toEqual({ id: 'bob', role: 'employee' });
    expect(s.mode).toBe('plan');
    expect(s.trace).toHaveLength(1);
    expect(s.toolCalls).toHaveLength(1);
    expect(s.judge[0].action).toBe('accept');
    expect(s.result.agent_status).toBe('answered');
    expect(s.lastEventId).toBe('1008-0');
    expect(s.events).toHaveLength(EVENTS.length);
  });

  it('merges step updates into the plan steps', () => {
    const s = play(EVENTS.slice(0, 5));
    const steps = planSteps(s, latestPlan(s).version);
    expect(steps.map((x) => x.status)).toEqual(['done', 'pending']);
    expect(steps[0]).toMatchObject({ relevant: 3, best: 0.92 });
  });

  it('ignores events it has already seen (resume overlap)', () => {
    const s = play([...EVENTS.slice(0, 4), ...EVENTS.slice(2, 4)]);
    expect(s.events).toHaveLength(4);
  });

  it('keeps re-plans as separate versions', () => {
    const replan = {
      id: '2000-0',
      event: 'plan',
      data: { version: 2, label: 'replan', rationale: 'retry', steps: [step(1, 'pending', { version: 2 })] },
    };
    const s = play([...EVENTS.slice(0, 5), replan]);
    expect(s.plans.map((p) => p.version)).toEqual([1, 2]);
    expect(latestPlan(s).label).toBe('replan');
  });

  it('records an error problem and counts replayed events', () => {
    let s = runReducer(initialRunState('r1'), { type: 'connecting', resuming: true });
    s = runReducer(s, {
      type: 'event',
      event: { id: 'db-1', event: 'error', data: { status: 504, title: 'Agent timeout' } },
      replayed: true,
    });
    s = runReducer(s, {
      type: 'event',
      event: { id: 'db-2', event: 'done', data: { status: 'timeout' } },
      replayed: true,
    });
    expect(s.problem.status).toBe(504);
    expect(s.finalStatus).toBe('timeout');
    expect(s.replayedCount).toBe(2);
  });

  it('detaches without losing state, and closes as detached when there was no `done`', () => {
    let s = play(EVENTS.slice(0, 4));
    s = runReducer(s, { type: 'detach' });
    expect(s.phase).toBe('detached');
    expect(runReducer(s, { type: 'closed' }).phase).toBe('detached');
    expect(s.lastEventId).toBe('1003-0');
  });
});
