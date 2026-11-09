import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { copyFor, slugOf } from '../../lib/problem';
import { ReadinessList } from '../ReadinessList';
import { Icon, Pill } from '../ui';
import { ProblemPanel } from './ProblemPanel';

function Shell({ tone, code, title, badge, children }) {
  const dot = { warn: 'bg-dot-warn', bad: 'bg-dot-bad', mute: 'bg-dot-mute' }[tone];
  return (
    <section role="alert" className="card space-y-3 p-5">
      <header className="flex items-start justify-between gap-3">
        <h3 className="flex items-center gap-2 text-base font-semibold">
          <span className={`size-2.5 rounded-full ${dot}`} />
          {code && <span className="font-mono">{code} ·</span>} {title}
        </h3>
        {badge}
      </header>
      {children}
    </section>
  );
}

/** 504 agent-timeout: the run may still finish; offer the result URL and a longer budget. */
export function TimeoutCard({ problem, requestId, question, mode }) {
  const navigate = useNavigate();
  const id = requestId || problem?.request_id;
  return (
    <Shell tone="bad" code={problem?.status || 504} title={copyFor('agent-timeout').title}>
      <p className="text-sm text-ink-2">{problem?.detail || copyFor('agent-timeout').hint}</p>
      <div className="flex flex-wrap justify-between gap-2 pt-1">
        {id && (
          <Link to={`/requests/${id}`} className="btn-ghost">
            <Icon name="hourglass_top" className="text-base!" /> Check result later
          </Link>
        )}
        {question && (
          <button
            type="button"
            className="btn-primary"
            onClick={() => navigate('/', { state: { question, mode, timeout: 300 } })}
          >
            Try again with a longer time budget <Icon name="timer" className="text-base!" />
          </button>
        )}
      </div>
      <ProblemPanel problem={problem} />
    </Shell>
  );
}

/** 503 not-ready / agent-failed: show which subsystem is down (live /ready). */
export function UnavailableCard({ problem }) {
  const ready = useQuery({ queryKey: keys.ready, queryFn: api.ready, retry: false });
  const checks = ready.data?.checks || ready.error?.problem?.checks || problem?.checks;
  const slug = slugOf(problem?.type);
  return (
    <Shell
      tone="bad"
      code={problem?.status || 503}
      title={copyFor(slug).title}
      badge={<Pill tone="bad">DEGRADED</Pill>}
    >
      <p className="text-sm text-ink-2">{problem?.detail || copyFor(slug).hint}</p>
      {checks && (
        <div className="space-y-2">
          <p className="label">Upstream health</p>
          <ReadinessList checks={checks} />
        </div>
      )}
      <ProblemPanel problem={problem} />
    </Shell>
  );
}

/** Any other problem (404, 500, network). */
export function GenericErrorCard({ problem, onRetry }) {
  const slug = problem?.type ? slugOf(problem.type) : 'network';
  const copy = copyFor(slug);
  return (
    <Shell tone="mute" code={problem?.status || null} title={problem?.title || copy.title}>
      <p className="text-sm text-ink-2">{problem?.detail || copy.hint}</p>
      {onRetry && (
        <button type="button" className="btn-ghost" onClick={onRetry}>
          <Icon name="refresh" className="text-base!" /> Try again
        </button>
      )}
      <ProblemPanel problem={problem} />
    </Shell>
  );
}

/** Pick the right card for an ApiError or a raw problem object. */
export function ErrorView({ error, problem: raw, requestId, question, mode, onRetry }) {
  const problem =
    raw || error?.problem || (error ? { title: 'Error', detail: String(error.message || error) } : null);
  if (!problem) return null;
  const slug = problem.type ? slugOf(problem.type) : error?.slug;
  if (slug === 'agent-timeout') return <TimeoutCard {...{ problem, requestId, question, mode }} />;
  if (slug === 'not-ready' || slug === 'agent-failed') return <UnavailableCard problem={problem} />;
  return <GenericErrorCard problem={problem} onRetry={onRetry} />;
}
