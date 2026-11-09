import { score } from '../../lib/format';

/** One-line, human-readable summary of an SSE event (live log and request-detail feed). */
export function summarizeEvent({ event, data }) {
  const d = data || {};
  switch (event) {
    case 'accepted':
      return `user ${d.user?.id ?? '?'} (${d.user?.role ?? '?'}) · mode ${d.options?.mode ?? '?'} · budget ${
        d.options?.timeout_seconds ?? '?'
      } s`;
    case 'plan':
      return `v${d.version} · ${(d.steps || []).length} steps${d.rationale ? ` · ${d.rationale}` : ''}`;
    case 'step':
      return d.status === 'running'
        ? `step ${d.id} running · ${d.tool ?? ''} “${d.query ?? ''}”`
        : `step ${d.id} ${d.status}${d.relevant !== undefined ? ` · ${d.relevant} relevant · best ${score(d.best)}` : ''}`;
    case 'tool_call':
      return `${d.name} · ${d.origin} · ${d.status}${d.seconds ? ` · ${d.seconds} s` : ''}`;
    case 'trace':
      return `${d.step} · ${d.decision}${d.detail ? ` · ${String(d.detail).slice(0, 120)}` : ''}`;
    case 'judge': {
      const scores = Object.entries(d.scores || {})
        .map(([k, v]) => `${k.replace(/_/g, ' ')} ${score(v)}`)
        .join(' · ');
      return `attempt ${d.attempt} · ${d.action || (d.passed ? 'accept' : 'fail')}${scores ? ` · ${scores}` : ''}`;
    }
    case 'result':
      return `agent_status ${d.agent_status} · judge ${
        d.judge?.passed === null || d.judge?.passed === undefined
          ? 'n/a'
          : d.judge.passed
            ? 'passed'
            : 'failed'
      } · ${(d.sources || []).length} sources`;
    case 'error':
      return `${d.status ?? ''} ${d.title ?? 'error'}${d.detail ? ` · ${d.detail}` : ''}`.trim();
    case 'done':
      return `status ${d.status}`;
    default:
      return typeof data === 'string' ? data : JSON.stringify(data).slice(0, 140);
  }
}

/** Tone used for the event chip / timeline dot. */
export function eventTone(event, data) {
  if (event === 'error') return 'bad';
  if (event === 'done' || event === 'result') return 'ok';
  if (event === 'judge') return data?.passed ? 'ok' : 'warn';
  if (event === 'accepted') return 'mute';
  return 'info';
}
