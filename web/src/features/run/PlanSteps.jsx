import { Icon, Spinner } from '../../components/ui';
import { score } from '../../lib/format';

const STEP_STATUS = {
  done: { icon: 'check_circle', cls: 'text-ok' },
  running: { spinner: true, cls: 'text-info' },
  no_results: { icon: 'error', cls: 'text-warn' },
  replanned: { icon: 'alt_route', cls: 'text-warn' },
  skipped: { icon: 'block', cls: 'text-ink-3' },
  pending: { icon: 'radio_button_unchecked', cls: 'text-ink-3' },
};

function StepIcon({ status }) {
  const s = STEP_STATUS[status] || STEP_STATUS.pending;
  if (s.spinner) return <Spinner className="mt-0.5 border-info-line border-t-info" />;
  return <Icon name={s.icon} className={`text-lg! ${s.cls}`} />;
}

/** One plan version: rationale + its steps with live/final status. */
export function PlanSteps({ plan, steps, compact = false }) {
  return (
    <div className={`rounded-xl bg-well ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="label">
            {plan.label && plan.label !== 'plan' ? `${plan.label} ` : 'Plan '}v{plan.version}
          </p>
          {plan.rationale && (
            <p className={`mt-1 font-semibold ${compact ? 'text-sm' : 'text-base'}`}>{plan.rationale}</p>
          )}
        </div>
        <span className="shrink-0 rounded-md bg-card px-2 py-0.5 font-mono text-xs text-ink-2">
          {steps.length} {steps.length === 1 ? 'step' : 'steps'}
        </span>
      </div>
      <ol className="mt-3 space-y-3">
        {steps.map((s) => (
          <li key={`${s.version}-${s.id}`} className="flex gap-2.5">
            <StepIcon status={s.status} />
            <div className="min-w-0 flex-1 text-sm">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-[13px] font-medium">{s.tool}</span>
                {(s.domains || []).map((d) => (
                  <span key={d} className="rounded bg-info-bg px-1.5 py-0.5 font-mono text-[11px] text-info">
                    domain: {d}
                  </span>
                ))}
                <span className="truncate text-ink-2 italic">“{s.query}”</span>
              </div>
              {s.goal && !compact && <p className="mt-0.5 text-xs text-ink-2">{s.goal}</p>}
              <p className="mt-0.5 font-mono text-xs text-ink-3">
                {s.status || 'pending'}
                {s.status !== 'pending' && s.status !== 'running' && (
                  <>
                    {' '}
                    · {s.relevant ?? 0} relevant · best {score(s.best)}
                    {s.seconds ? ` · ${s.seconds} s` : ''}
                  </>
                )}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
