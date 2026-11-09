import { Dot, EmptyState, Icon, Pill } from '../../../components/ui';
import { score } from '../../../lib/format';

const label = (k) => k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

/** LLM-as-judge: scores against thresholds, and every attempt with the escalation taken. */
export function JudgeTab({ judge }) {
  if (!judge || judge.passed === null || judge.passed === undefined) {
    return (
      <EmptyState icon="gavel" title="The judge did not run">
        Cache hits, guardrail blocks and no-info answers skip the quality judge.
      </EmptyState>
    );
  }
  const names = Object.keys({ ...judge.thresholds, ...judge.scores });
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-semibold">
          Judge LLM <Dot tone={judge.passed ? 'ok' : 'bad'} />
        </span>
        {judge.model && (
          <span className="rounded-md bg-well px-2 py-0.5 font-mono text-xs">{judge.model}</span>
        )}
      </div>
      <ul className="space-y-4">
        {names.map((k) => {
          const value = judge.scores?.[k];
          const target = judge.thresholds?.[k];
          const pass = typeof value === 'number' && (target === undefined || value >= target);
          return (
            <li key={k}>
              <div className="flex items-center justify-between text-sm">
                <span>{label(k)}</span>
                <span className="font-mono text-xs text-ink-2">
                  {target !== undefined && <>Target ≥{score(target)} </>}
                  <span
                    className={`ml-1 rounded px-1 font-semibold ${pass ? 'bg-ok-bg text-ok' : 'bg-bad-bg text-bad'}`}
                  >
                    {score(value)}
                  </span>
                </span>
              </div>
              <div className="relative mt-1.5 h-1.5 rounded-full bg-well">
                <span
                  className={`block h-full rounded-full ${pass ? 'bg-dot-ok' : 'bg-dot-bad'}`}
                  style={{ width: `${Math.round((value || 0) * 100)}%` }}
                />
                {target !== undefined && (
                  <span
                    aria-hidden="true"
                    className="absolute -top-0.5 h-2.5 w-0.5 bg-ink-3"
                    style={{ left: `${Math.round(target * 100)}%` }}
                  />
                )}
              </div>
            </li>
          );
        })}
      </ul>
      <ul className="space-y-2">
        {(judge.attempts || []).map((a) => (
          <li
            key={a.attempt}
            className="flex items-center justify-between rounded-lg bg-well px-3 py-2 text-sm"
          >
            <span className="flex items-center gap-2">
              <Icon
                name={a.passed ? 'check_circle' : 'cancel'}
                className={`text-lg! ${a.passed ? 'text-ok' : 'text-bad'}`}
              />
              Attempt #{a.attempt} {a.action || (a.passed ? 'accepted' : 'failed')}
              {a.failed?.length > 0 && <Pill tone="bad">{a.failed.join(', ')}</Pill>}
            </span>
            <span className="font-mono text-xs text-ink-3">{a.seconds} s</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
