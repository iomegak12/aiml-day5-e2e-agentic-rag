import { formatDateTime, formatSeconds, score } from '../../../lib/format';

function Row({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 text-sm">
      <dt className="text-ink-2">{label}</dt>
      <dd className="text-right font-mono text-[13px]">{children}</dd>
    </div>
  );
}

/** Timings, cache and routing facts for one run. */
export function TimingTab({ result }) {
  const t = result.timings || {};
  const total = t.total_s || 0;
  const parts = [
    { label: 'Queued', value: t.queued_s || 0, cls: 'bg-dot-mute' },
    { label: 'Agent', value: t.agent_s || 0, cls: 'bg-dot-info' },
  ];
  return (
    <div className="space-y-4">
      {total > 0 && (
        <div>
          <div className="flex h-2 overflow-hidden rounded-full bg-well">
            {parts.map((p) => (
              <span key={p.label} className={p.cls} style={{ width: `${(p.value / total) * 100}%` }} />
            ))}
          </div>
          <p className="mt-1 flex gap-3 text-xs text-ink-3">
            {parts.map((p) => (
              <span key={p.label}>
                {p.label} {formatSeconds(p.value)}
              </span>
            ))}
          </p>
        </div>
      )}
      <dl className="divide-y divide-line">
        <Row label="Total (API)">{formatSeconds(t.total_s)}</Row>
        <Row label="Inside the agent">{formatSeconds(t.agent_s)}</Row>
        <Row label="Waiting for a worker">{formatSeconds(t.queued_s)}</Row>
        <Row label="Started">{formatDateTime(t.started_at)}</Row>
        <Row label="Finished">{formatDateTime(t.finished_at)}</Row>
        <Row label="Mode">{result.mode}</Row>
        <Row label="Routes">{result.routes?.length ? result.routes.join(' → ') : '–'}</Row>
        <Row label={result.mode === 'plan' ? 'Re-plans' : 'Query rewrites'}>{result.rewrites ?? 0}</Row>
        <Row label="Semantic cache">
          {result.cache?.hit ? `hit (similarity ${score(result.cache.similarity)})` : 'miss'}
        </Row>
        {result.cache?.cached_question && <Row label="Cached question">{result.cache.cached_question}</Row>}
      </dl>
    </div>
  );
}
