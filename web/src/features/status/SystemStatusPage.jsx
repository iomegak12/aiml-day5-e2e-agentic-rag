import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { ProblemPanel } from '../../components/errors/ProblemPanel';
import { ReadinessList } from '../../components/ReadinessList';
import { Icon, Pill, Spinner } from '../../components/ui';
import { RequireAdmin } from '../auth/guards';

const REFRESH_MS = 15_000;

function ProbeCard({ title, path, children, ok, pending }) {
  return (
    <section className="card space-y-3 p-5">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold">{title}</h2>
          <code className="font-mono text-xs text-ink-3">GET {path}</code>
        </div>
        {pending ? (
          <Spinner />
        ) : (
          <Pill tone={ok ? 'ok' : 'bad'} dot>
            {ok ? 'OK' : 'Failing'}
          </Pill>
        )}
      </header>
      {children}
    </section>
  );
}

function StatusContent() {
  const health = useQuery({
    queryKey: keys.health,
    queryFn: api.health,
    refetchInterval: REFRESH_MS,
    retry: false,
  });
  const ready = useQuery({
    queryKey: keys.ready,
    queryFn: api.ready,
    refetchInterval: REFRESH_MS,
    retry: false,
  });
  // /ready answers 503 + problem (with the same checks) when a dependency is down.
  const checks = ready.data?.checks || ready.error?.problem?.checks;
  const down = checks
    ? Object.entries(checks)
        .filter(([, c]) => c.status !== 'up')
        .map(([n]) => n)
    : [];
  const allOk = health.isSuccess && ready.isSuccess;
  const updated = Math.max(health.dataUpdatedAt, ready.dataUpdatedAt, ready.errorUpdatedAt);

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-6 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">System status</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-ink-2">
            {health.isPending || ready.isPending ? (
              'Checking…'
            ) : allOk ? (
              <>
                <Icon name="check_circle" className="text-base! text-ok" /> All systems operational
              </>
            ) : (
              <>
                <Icon name="warning" className="text-base! text-bad" /> Degraded
                {down.length ? `: ${down.join(', ')} unavailable` : ''}
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-ink-3">
          {updated > 0 && <span>Updated {new Date(updated).toLocaleTimeString()} · every 15 s</span>}
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              health.refetch();
              ready.refetch();
            }}
          >
            <Icon name="refresh" className="text-base!" /> Refresh
          </button>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <ProbeCard title="Liveness" path="/health" ok={health.isSuccess} pending={health.isPending}>
          {health.isSuccess ? (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-well p-3">
                <dt className="text-xs text-ink-2">Process</dt>
                <dd className="font-semibold">{health.data.status}</dd>
              </div>
              <div className="rounded-lg bg-well p-3">
                <dt className="text-xs text-ink-2">API version</dt>
                <dd className="font-mono font-semibold">v{health.data.version}</dd>
              </div>
            </dl>
          ) : (
            health.isError && <ProblemPanel problem={health.error.problem} defaultOpen />
          )}
        </ProbeCard>

        <ProbeCard title="Readiness" path="/ready" ok={ready.isSuccess} pending={ready.isPending}>
          {checks ? (
            <ReadinessList checks={checks} />
          ) : (
            ready.isError && <ProblemPanel problem={ready.error.problem} defaultOpen />
          )}
        </ProbeCard>
      </div>

      <section className="card flex items-start gap-3 p-4 text-sm text-ink-2">
        <Icon name="info" className="text-ink-3" />
        <p>
          Prometheus <code className="font-mono">/metrics</code> is intentionally not exposed through the web
          gateway (it is unauthenticated). Scrape it from the API container network, or open{' '}
          <code className="font-mono">http://localhost:8080/metrics</code> on the host.
        </p>
      </section>
    </div>
  );
}

/** Screen 08 (admin only): liveness and readiness probes, auto-refreshing. */
export default function SystemStatusPage() {
  return (
    <RequireAdmin>
      <StatusContent />
    </RequireAdmin>
  );
}
