import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { ErrorView } from '../../components/errors/ErrorCards';
import { StatusBadge } from '../../components/StatusBadge';
import { CopyButton } from '../../components/Toast';
import { Icon, PageLoader, Pill, Spinner } from '../../components/ui';
import { useElapsed } from '../../hooks/useCountdown';
import { eventTimeMs, formatClock, formatSeconds, shortId } from '../../lib/format';
import { Composer } from '../chat/Composer';
import { useAsk } from '../chat/useAsk';
import { EventLog } from './EventLog';
import { PlanSteps } from './PlanSteps';
import { attach, detach, useRun } from './runStore';
import { latestPlan, planSteps } from './runReducer';
import { TraceConsole } from './TraceConsole';

function runStatusOf(run) {
  if (run.finalStatus) return run.finalStatus;
  if (run.problem?.status === 504) return 'timeout';
  if (run.problem) return 'failed';
  return 'running';
}

/** Screen 03: the run streaming live over SSE (plan, steps, trace, judge), then "View answer". */
export default function LiveRunPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const run = useRun(id);
  const ask = useAsk();
  const detail = useQuery({ queryKey: keys.request(id), queryFn: () => api.getRequest(id) });

  // Not started from this tab (refresh, link, history): attach and replay the buffered events.
  useEffect(() => {
    attach(id);
  }, [id]);

  const firstMs = eventTimeMs(run?.events[0]?.id);
  const startedAt = firstMs || (detail.data?.created_at ? Date.parse(detail.data.created_at) : null);
  const live = run && !run.finalStatus && run.phase !== 'error';
  const elapsed = useElapsed(startedAt, Boolean(live));

  if (!run) return <PageLoader label="Connecting to the run…" />;
  if (detail.isError && detail.error.status === 404) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <ErrorView error={detail.error} />
      </div>
    );
  }

  const question = run.question || detail.data?.question;
  const mode = run.mode || detail.data?.mode;
  const status = runStatusOf(run);
  const plan = latestPlan(run);
  const finished = Boolean(run.finalStatus);
  const total = run.result?.timings?.total_s;
  const answerReady = run.result && (status === 'completed' || status === 'client_disconnected');

  function stopWatching() {
    detach(id);
    navigate(`/requests/${id}`);
  }

  return (
    <div className="flex min-h-full">
      <div className="min-w-0 flex-1 px-4 py-5 sm:px-6">
        <div className="mx-auto max-w-3xl space-y-5 pb-44">
          <div className="flex items-center justify-between gap-3 font-mono text-xs text-ink-2">
            <span className="flex items-center gap-2 uppercase">
              POST /api/v1/agent/ask/stream
              {mode && <Pill tone="info">mode: {mode}</Pill>}
            </span>
            <span className="hidden items-center gap-1 sm:flex">
              <Icon name="stream" className="text-base!" /> text/event-stream
            </span>
          </div>

          {question && (
            <div className="ml-auto max-w-[85%] rounded-2xl bg-well px-5 py-4 text-[15px] leading-7">
              {question}
            </div>
          )}

          <section className="card space-y-4 p-5">
            <header className="flex flex-wrap items-center gap-2">
              <StatusBadge status={status} />
              <span className="inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 font-mono text-xs">
                <Icon name="schedule" className="text-sm!" />
                {finished && total ? formatSeconds(total) : formatClock(elapsed)}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-line pl-2 font-mono text-xs">
                {shortId(id)} <CopyButton text={id} label="Copy request id" iconOnly />
              </span>
              <span className="ml-auto">
                {live && run.phase !== 'detached' && (
                  <button
                    type="button"
                    onClick={stopWatching}
                    className="text-sm underline underline-offset-2"
                  >
                    Stop watching
                  </button>
                )}
              </span>
            </header>

            {run.phase === 'connecting' && !run.events.length && (
              <p className="flex items-center gap-2 text-sm text-ink-2">
                <Spinner /> Connecting to the event stream…
              </p>
            )}

            {answerReady && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ok-line bg-ok-bg px-4 py-3 text-ok">
                <span className="flex items-center gap-2 text-sm font-medium">
                  <Icon name="check_circle" />
                  Answer ready · {run.result.agent_status}
                  {run.result.judge?.passed === true && ' · judge passed'}
                  {total ? ` · ${formatSeconds(total)}` : ''}
                </span>
                <Link to={`/runs/${id}`} className="btn-primary">
                  View answer <Icon name="arrow_forward" className="text-base!" />
                </Link>
              </div>
            )}

            {run.problem && (
              <ErrorView problem={run.problem} requestId={id} question={question} mode={mode} />
            )}

            {run.phase === 'error' && run.connectionError && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-warn-line bg-warn-bg px-4 py-3 text-sm text-warn">
                <span className="flex items-center gap-2">
                  <Icon name="wifi_off" /> Connection lost. The run continues on the server.
                </span>
                <button type="button" className="btn-ghost" onClick={() => attach(id)}>
                  Resume with Last-Event-ID
                </button>
              </div>
            )}

            {plan && <PlanSteps plan={plan} steps={planSteps(run, plan.version)} />}

            {!plan && mode === 'react' && run.toolCalls.length > 0 && (
              <ul className="space-y-1 rounded-xl bg-well p-4 font-mono text-xs">
                {run.toolCalls.map((c) => (
                  <li key={c.seq}>
                    #{c.seq} {c.name} · {c.origin} · {c.status}
                  </li>
                ))}
              </ul>
            )}

            {run.judge.length > 0 && !finished && (
              <p className="flex items-center gap-2 text-sm text-ink-2">
                <Spinner /> Judge evaluating… attempt {run.judge[run.judge.length - 1].attempt} (
                {run.judge[run.judge.length - 1].action})
              </p>
            )}

            {run.trace.length > 0 && (
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="label">Live activity (event: trace)</p>
                  {live && <span className="font-mono text-xs text-ink-3">streaming</span>}
                </div>
                <TraceConsole trace={run.trace} live={live} />
              </div>
            )}
          </section>
        </div>

        <div className="pointer-events-none sticky bottom-0 -mx-4 bg-gradient-to-t from-canvas via-canvas to-transparent px-4 pt-8 pb-4 sm:-mx-6 sm:px-6">
          <div className="pointer-events-auto mx-auto max-w-3xl">
            <Composer
              key={finished ? 'done' : 'live'}
              compact
              disabled={!finished}
              disabledHint="Waiting for the answer…"
              placeholder="Ask a follow-up question…"
              onSubmit={ask.submit}
              pending={ask.pending}
              error={ask.error}
              onClearError={ask.clearError}
              initial={{ mode }}
            />
          </div>
        </div>
      </div>

      <aside className="hidden w-96 shrink-0 border-l border-line bg-card xl:block">
        <div className="sticky top-0 flex max-h-[calc(100vh-3.5rem)] flex-col">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h2 className="flex items-center gap-2 font-semibold">
              <Icon name="sensors" /> Live events (SSE)
            </h2>
            <Pill tone={live ? 'info' : run.phase === 'detached' ? 'warn' : 'mute'}>
              {live ? (run.phase === 'detached' ? 'detached' : 'streaming') : 'closed'}
            </Pill>
          </div>
          <p className="px-5 pt-3 text-xs text-ink-2">
            Each event has an id. If the connection drops, resume with GET /requests/{'{id}'}/events and
            Last-Event-ID.
          </p>
          <div className="scroll-thin flex-1 overflow-y-auto px-5 pb-4">
            <EventLog events={run.events} live={live} />
          </div>
        </div>
      </aside>
    </div>
  );
}
