import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { ErrorView } from '../../components/errors/ErrorCards';
import { StatusBadge } from '../../components/StatusBadge';
import { CopyButton } from '../../components/Toast';
import { Avatar, EmptyState, Icon, PageLoader, Pill } from '../../components/ui';
import { eventTimeMs, formatSeconds, formatTime, shortId } from '../../lib/format';
import { eventTone, summarizeEvent } from '../run/eventSummary';
import { attach, getRun, useRun } from '../run/runStore';

const DOT = {
  ok: 'bg-dot-ok',
  warn: 'bg-dot-warn',
  bad: 'bg-dot-bad',
  info: 'bg-dot-info',
  mute: 'bg-dot-mute',
};
const CHIP = {
  ok: 'bg-ok-bg text-ok',
  warn: 'bg-warn-bg text-warn',
  bad: 'bg-bad-bg text-bad',
  info: 'bg-info-bg text-info',
  mute: 'bg-well text-ink-2',
};

function Box({ label, children, sub }) {
  return (
    <div className="rounded-lg bg-well p-3">
      <p className="text-xs text-ink-2">{label}</p>
      <div className="mt-0.5 text-lg font-semibold">{children}</div>
      {sub && <p className="font-mono text-xs text-ink-3">{sub}</p>}
    </div>
  );
}

/** Screen 06: one run's metadata and its event timeline, replayed (and resumed live) from /events. */
export default function RequestDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const detail = useQuery({
    queryKey: keys.request(id),
    queryFn: () => api.getRequest(id),
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 5_000 : false),
  });
  const run = useRun(id);

  // Fresh visit: replay every buffered event, then follow live. After "Stop watching" we stay detached until the
  // user clicks Resume, which sends Last-Event-ID and replays only the missed events.
  const found = detail.isSuccess;
  useEffect(() => {
    if (found && getRun(id)?.phase !== 'detached') attach(id);
  }, [found, id]);

  if (detail.isPending) return <PageLoader label="Loading request…" />;
  if (detail.isError) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <ErrorView error={detail.error} onRetry={detail.refetch} />
      </div>
    );
  }

  const d = detail.data;
  const events = run?.events || [];
  const firstMs = eventTimeMs(events[0]?.id);
  const lastId = run?.lastEventId;
  const resumed = run?.resuming && run.replayedCount > 0;
  const following = run && !run.finalStatus && (run.phase === 'streaming' || run.phase === 'connecting');
  const budget = run?.options?.timeout_seconds; // from the `accepted` event
  const status = run?.finalStatus || d.status;

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm">
          <Link to="/requests" className="flex items-center gap-1 text-ink-2 hover:text-ink">
            <Icon name="arrow_back" className="text-base!" /> Requests
          </Link>
          <span className="text-ink-3">/</span>
          <span className="inline-flex items-center gap-1 rounded-md bg-well pl-2 font-mono text-xs">
            {shortId(id)} <CopyButton text={id} label="Copy request id" iconOnly />
          </span>
        </nav>
        <div className="flex gap-2">
          {status === 'completed' || status === 'client_disconnected' ? (
            <Link to={`/runs/${id}`} className="btn-ghost">
              <Icon name="article" className="text-base!" /> Open answer
            </Link>
          ) : null}
          <button
            type="button"
            className="btn-ghost"
            onClick={() =>
              navigate('/', { state: { question: d.question, mode: d.mode, fresh: Date.now() } })
            }
          >
            <Icon name="refresh" className="text-base!" /> Ask again
          </button>
        </div>
      </div>

      {run?.phase === 'detached' && (
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-info-line bg-info-bg p-4">
          <div className="flex gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-info">
              <Icon name="link_off" />
            </span>
            <div>
              <h2 className="font-semibold">You stopped watching</h2>
              <p className="mt-1 max-w-2xl text-sm text-ink-2">
                The run keeps going on the server. Resume to replay the events you missed after Last-Event-ID{' '}
                <code className="font-mono text-xs">{lastId}</code>, then follow it live.
              </p>
            </div>
          </div>
          <button type="button" className="btn-primary" onClick={() => attach(id)}>
            <Icon name="replay" className="text-base!" /> Resume stream
          </button>
        </section>
      )}

      {resumed && (
        <section className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-warn-line bg-warn-bg p-4">
          <div className="flex gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-warn">
              <Icon name="settings_input_antenna" />
            </span>
            <div>
              <h2 className="flex flex-wrap items-center gap-2 font-semibold">
                Connection resumed
                <Pill tone="warn">
                  <Icon name="history" className="text-sm!" /> Replayed {run.replayedCount} missed events
                </Pill>
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-ink-2">
                You stopped watching, but the run continued on the server (it is decoupled from the HTTP
                connection). The missed events were replayed from the Redis Stream after your Last-Event-ID.
              </p>
            </div>
          </div>
          <Pill tone={following ? 'ok' : 'mute'} dot pulse={following}>
            {following ? 'Live synchronized' : 'Stream closed'}
          </Pill>
        </section>
      )}

      <section className="card grid gap-6 p-5 lg:grid-cols-2">
        <div className="space-y-3">
          <p className="label">Invocation metadata</p>
          <div className="flex items-center justify-between rounded-lg bg-well px-3 py-2">
            <div className="min-w-0">
              <p className="text-xs text-ink-2">Request ID</p>
              <p className="truncate font-mono text-sm">{id}</p>
            </div>
            <CopyButton text={id} label="Copy request id" iconOnly />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-3 rounded-lg bg-well p-3">
              <Avatar name={d.user_id} />
              <div>
                <p className="text-xs text-ink-2">Operator</p>
                <p className="font-medium">{d.user_id}</p>
              </div>
            </div>
            <div className="rounded-lg bg-well p-3">
              <p className="text-xs text-ink-2">Execution strategy</p>
              <p className="mt-1 flex flex-wrap gap-1">
                <Pill tone="info">Mode: {d.mode === 'react' ? 'ReAct' : 'Plan'}</Pill>
                <Pill tone="mute">{d.endpoint}</Pill>
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          <p className="label">Lifecycle and state</p>
          <div className="flex flex-wrap items-center gap-2">
            {d.client_disconnected && (
              <>
                <Pill tone="warn" dot>
                  Client dropped
                </Pill>
                <Icon name="arrow_forward" className="text-base! text-ink-3" />
              </>
            )}
            <StatusBadge status={status} />
            {d.agent_status && <Pill tone="mute">{d.agent_status}</Pill>}
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Box label="Created" sub={new Date(d.created_at).toLocaleDateString()}>
              {formatTime(d.created_at)}
            </Box>
            <Box label="Duration" sub={budget ? `budget ${budget} s` : null}>
              {formatSeconds(d.elapsed_s)}
            </Box>
            <Box label="Last event ID" sub={`${events.length} events`}>
              <span className="block truncate font-mono text-sm">{lastId || '–'}</span>
            </Box>
          </div>
        </div>
      </section>

      {d.error && status !== 'completed' && (
        <ErrorView problem={d.error} requestId={id} question={d.question} mode={d.mode} />
      )}

      <section className="card p-5">
        <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Icon name="timeline" /> Execution event feed
            <span className="rounded-md bg-well px-2 py-0.5 font-mono text-xs font-normal">
              {events.length} total
            </span>
          </h2>
          <span className="flex items-center gap-3 text-xs text-ink-2">
            {following && (
              <Pill tone="info" dot pulse>
                Live
              </Pill>
            )}
            {resumed && (
              <span className="flex items-center gap-1">
                <span className="size-2.5 rounded-sm bg-dot-warn" /> Replayed during recovery
              </span>
            )}
          </span>
        </header>
        {!events.length ? (
          <EmptyState
            icon="stream"
            title={run?.phase === 'error' ? 'Could not load events' : 'Replaying events…'}
          >
            {run?.connectionError?.message}
          </EmptyState>
        ) : (
          <ol className="relative space-y-1 before:absolute before:top-2 before:bottom-2 before:left-[5px] before:w-px before:bg-line">
            {events.map((e, i) => {
              const tone = eventTone(e.event, e.data);
              const ms = eventTimeMs(e.id);
              const rel = ms && firstMs ? (ms - firstMs) / 1000 : null;
              return (
                <li
                  key={e.id || i}
                  className={`relative grid grid-cols-[auto_4.5rem_auto_1fr_auto] items-start gap-3 rounded-lg py-2 pr-2 text-sm ${
                    e.replayed ? 'bg-warn-bg' : ''
                  }`}
                >
                  <span className={`relative mt-1 size-[11px] rounded-full ring-4 ring-card ${DOT[tone]}`} />
                  <span className="font-mono text-xs text-ink-3">
                    {rel === null ? '—' : `${rel.toFixed(1)} s`}
                  </span>
                  <span className={`rounded px-1.5 py-0.5 font-mono text-xs ${CHIP[tone]}`}>{e.event}</span>
                  <span className="min-w-0 break-words text-ink-2">
                    {summarizeEvent(e)}
                    {e.replayed && (
                      <Pill tone="warn" className="ml-2">
                        replayed
                      </Pill>
                    )}
                  </span>
                  <span className="hidden font-mono text-[11px] text-ink-3 sm:inline">{e.id}</span>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}
