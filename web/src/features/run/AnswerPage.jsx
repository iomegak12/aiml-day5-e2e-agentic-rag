import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { ErrorView } from '../../components/errors/ErrorCards';
import { OutcomeBadge } from '../../components/StatusBadge';
import { CopyButton } from '../../components/Toast';
import { Avatar, Icon, PageLoader, Pill } from '../../components/ui';
import { formatSeconds, formatTime } from '../../lib/format';
import { Composer } from '../chat/Composer';
import { useAsk } from '../chat/useAsk';
import { useAuth } from '../auth/useAuth';
import { AnswerMarkdown } from './AnswerMarkdown';
import { sourceDomId } from './citations';
import { InsightsPanel } from './insights/InsightsPanel';

/** Screen 04: the answer with citation chips, and the Insights panel (plan, sources, judge, tools, trace, timing). */
export default function AnswerPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const ask = useAsk();
  const [tab, setTab] = useState('plan');
  const [highlight, setHighlight] = useState(null);
  const detail = useQuery({ queryKey: keys.request(id), queryFn: () => api.getRequest(id) });

  if (detail.isPending) return <PageLoader label="Loading the answer…" />;
  if (detail.isError) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <ErrorView error={detail.error} onRetry={detail.refetch} />
      </div>
    );
  }
  const run = detail.data;
  if (run.status === 'running') return <Navigate to={`/runs/${id}/live`} replace />;
  const result = run.result;

  function onCite(kbId) {
    setTab('sources');
    setHighlight(kbId);
    // after the Sources tab renders
    setTimeout(
      () =>
        document.getElementById(sourceDomId(kbId))?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
      50,
    );
  }

  return (
    <div className="flex min-h-full flex-col xl:flex-row">
      <div className="min-w-0 flex-1 px-4 py-5 sm:px-6">
        <div className="mx-auto max-w-3xl space-y-5 pb-44">
          <div className="flex items-start gap-3">
            <div className="ml-auto max-w-[85%] rounded-2xl bg-well px-5 py-4">
              <p className="label">
                User prompt <span className="ml-1 font-mono normal-case">{formatTime(run.created_at)}</span>
              </p>
              <p className="mt-1 text-[15px] leading-7">{run.question}</p>
            </div>
            <Avatar name={user.id === run.user_id ? user.name : run.user_id} />
          </div>

          {!result && (
            <ErrorView
              problem={run.error || { title: 'No result stored', detail: `Run status: ${run.status}` }}
              requestId={id}
              question={run.question}
              mode={run.mode}
            />
          )}

          {result && (
            <article className="card p-5 shadow-sm sm:p-6">
              <header className="mb-3 flex flex-wrap items-center gap-2">
                <span className="label">Answer</span>
                <OutcomeBadge agentStatus={result.agent_status} />
                {result.cache?.hit && <Pill tone="info">cache hit</Pill>}
                {run.status === 'client_disconnected' && <Pill tone="warn">finished after disconnect</Pill>}
                <span className="ml-auto flex items-center gap-1">
                  <CopyButton text={result.answer} label="Copy answer" />
                </span>
              </header>
              <AnswerMarkdown text={result.answer} onCite={onCite} />
              <footer className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 text-xs text-ink-3">
                <span className="font-mono">
                  {result.mode} · {formatSeconds(result.timings?.total_s)} · {result.sources?.length || 0}{' '}
                  sources
                </span>
                <Link to={`/requests/${id}`} className="inline-flex items-center gap-1 hover:text-ink">
                  <Icon name="timeline" className="text-sm!" /> Run details and events
                </Link>
              </footer>
            </article>
          )}
        </div>

        <div className="pointer-events-none sticky bottom-0 -mx-4 bg-gradient-to-t from-canvas via-canvas to-transparent px-4 pt-8 pb-4 sm:-mx-6 sm:px-6">
          <div className="pointer-events-auto mx-auto max-w-3xl">
            <Composer
              compact
              placeholder="Ask a follow-up question…"
              onSubmit={ask.submit}
              pending={ask.pending}
              error={ask.error}
              onClearError={ask.clearError}
              initial={{ mode: run.mode }}
            />
          </div>
        </div>
      </div>

      {result && (
        <aside className="w-full shrink-0 border-t border-line bg-canvas px-4 py-5 xl:w-[400px] xl:border-t-0 xl:border-l xl:px-5">
          <div className="xl:sticky xl:top-5">
            <InsightsPanel result={result} tab={tab} onTab={setTab} highlight={highlight} />
          </div>
        </aside>
      )}
    </div>
  );
}
