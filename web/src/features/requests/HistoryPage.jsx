import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ErrorView } from '../../components/errors/ErrorCards';
import { OutcomeBadge, StatusBadge } from '../../components/StatusBadge';
import { Avatar, EmptyState, Icon, PageLoader, Spinner } from '../../components/ui';
import { formatDateTime, formatSeconds } from '../../lib/format';
import { runLink } from '../../lib/routes';
import { useAuth } from '../auth/useAuth';
import { HistoryFilters } from './HistoryFilters';
import { filterRuns, runStats, useRequests } from './useRequests';

function Stat({ label, value }) {
  return (
    <div className="px-4">
      <p className="label">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold">{value}</p>
    </div>
  );
}

const FACTS = [
  { icon: 'hub', title: 'Owner-scoped', text: 'Non-admins see only their own requests (others are 404).' },
  { icon: 'verified_user', title: 'Stored results', text: 'agent_runs in Postgres, PII-redacted.' },
  { icon: 'bolt', title: 'Replay buffer', text: 'Live events kept 1 h (Redis Streams).' },
];

/** Screen 05: every question asked, with status, outcome and duration; filters and "Load more". */
export default function HistoryPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [status, setStatus] = useState('');
  const [mode, setMode] = useState('all');
  const q = useRequests({ status });
  const rows = filterRuns(q.items, { text, mode });
  const stats = runStats(q.items);

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold tracking-tight">
            Requests
            <code className="rounded-md bg-well px-2 py-0.5 font-mono text-xs font-normal">
              GET /api/v1/agent/requests
            </code>
          </h1>
          <p className="mt-1 text-ink-2">Every question you asked, with its status and result.</p>
        </div>
        <div className="card flex divide-x divide-line py-3">
          <Stat
            label="Avg latency"
            value={stats.avgLatency === null ? '–' : formatSeconds(stats.avgLatency)}
          />
          <Stat
            label="Cache hit rate"
            value={stats.cacheHitRate === null ? '–' : `${(stats.cacheHitRate * 100).toFixed(1)}%`}
          />
          <Stat label="Scope" value={isAdmin ? 'All users' : 'Own requests only'} />
        </div>
      </header>

      <HistoryFilters
        text={text}
        onText={setText}
        status={status}
        onStatus={setStatus}
        mode={mode}
        onMode={setMode}
      />

      <section className="card overflow-hidden">
        {q.isPending ? (
          <PageLoader label="Loading requests…" />
        ) : q.isError ? (
          <div className="p-4">
            <ErrorView error={q.error} onRetry={q.refetch} />
          </div>
        ) : !rows.length ? (
          <EmptyState icon="history" title="No matching requests">
            {q.items.length ? 'Try another filter.' : 'Ask a question to see it here.'}
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-well text-left">
                <tr className="label">
                  <th className="px-5 py-3 font-semibold">Question</th>
                  <th className="px-3 py-3 font-semibold">User</th>
                  <th className="px-3 py-3 font-semibold">Mode</th>
                  <th className="px-3 py-3 font-semibold">Status</th>
                  <th className="px-3 py-3 font-semibold">Outcome</th>
                  <th className="px-3 py-3 text-right font-semibold">Duration</th>
                  <th className="px-5 py-3 text-right font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <tr
                    key={r.request_id}
                    tabIndex={0}
                    onClick={() => navigate(runLink(r))}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(runLink(r))}
                    className="cursor-pointer hover:bg-well focus:bg-well focus:outline-none"
                  >
                    <td className="max-w-md px-5 py-4">
                      <p className="truncate font-medium">{r.question}</p>
                      <p className="truncate font-mono text-xs text-ink-3">{r.request_id}</p>
                    </td>
                    <td className="px-3 py-4">
                      <span className="flex items-center gap-2">
                        <Avatar name={r.user_id} size="sm" /> {r.user_id}
                      </span>
                    </td>
                    <td className="px-3 py-4">
                      <span className="rounded-md bg-well px-2 py-0.5 font-mono text-xs">
                        {r.mode === 'react' ? 'ReAct' : 'Plan'}
                      </span>
                    </td>
                    <td className="px-3 py-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-3 py-4">
                      <OutcomeBadge agentStatus={r.agent_status} />
                    </td>
                    <td className="px-3 py-4 text-right font-mono text-xs">{formatSeconds(r.elapsed_s)}</td>
                    <td className="px-5 py-4 text-right text-xs text-ink-2">
                      {formatDateTime(r.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {q.isSuccess && (
          <footer className="flex items-center justify-between border-t border-line px-5 py-3 text-sm text-ink-2">
            <span>
              Showing <strong className="text-ink">{rows.length}</strong>
              {q.hasNextPage ? ' of many' : ` of ${q.items.length}`}
            </span>
            {q.hasNextPage && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => q.fetchNextPage()}
                disabled={q.isFetchingNextPage}
              >
                {q.isFetchingNextPage ? <Spinner /> : <Icon name="expand_more" className="text-base!" />} Load
                more
              </button>
            )}
          </footer>
        )}
      </section>

      <div className="grid gap-3 md:grid-cols-3">
        {FACTS.map((f) => (
          <div key={f.title} className="card flex items-center gap-3 p-4">
            <span className="flex size-10 items-center justify-center rounded-full bg-well">
              <Icon name={f.icon} />
            </span>
            <span>
              <p className="text-sm font-medium">{f.title}</p>
              <p className="text-xs text-ink-2">{f.text}</p>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
