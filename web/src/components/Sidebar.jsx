import { useQuery } from '@tanstack/react-query';
import { Link, NavLink, useNavigate } from 'react-router';
import { api } from '../api/endpoints';
import { keys } from '../api/queryClient';
import { useAuth } from '../features/auth/useAuth';
import { MOD_LABEL } from '../hooks/useHotkey';
import { dayGroup } from '../lib/format';
import { runLink } from '../lib/routes';
import { statusTone } from '../lib/status';
import { Dot, Icon, Logo, Spinner } from './ui';
import { UserCard } from './UserCard';

const GROUPS = ['Today', 'Yesterday', 'Earlier'];

export function Sidebar({ onNavigate }) {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const history = useQuery({
    queryKey: keys.requests({ sidebar: true }),
    queryFn: () => api.listRequests({ limit: 20 }),
    refetchInterval: 30_000,
  });
  const items = history.data?.items || [];
  const grouped = GROUPS.map((g) => [g, items.filter((r) => dayGroup(r.created_at) === g)]).filter(
    ([, list]) => list.length,
  );

  return (
    <aside className="flex h-full w-60 flex-col border-r border-line bg-sidebar">
      <div className="flex h-14 items-center gap-2 px-4">
        <Link
          to="/"
          onClick={onNavigate}
          className="flex items-center gap-2 text-lg font-semibold tracking-tight"
        >
          <Logo size={28} /> NetCore Assist
        </Link>
      </div>
      <div className="px-2">
        <button
          type="button"
          onClick={() => {
            navigate('/', { state: { fresh: Date.now() } });
            onNavigate?.();
          }}
          className="flex w-full items-center justify-between rounded-full bg-primary px-4 py-2.5 text-sm font-medium text-on-primary hover:opacity-90"
        >
          <span className="flex items-center gap-2">
            <Icon name="add" className="text-lg!" /> New chat
          </span>
          <span className="rounded bg-white/15 px-1.5 py-0.5 font-mono text-[11px]">{MOD_LABEL}K</span>
        </button>
      </div>

      <nav aria-label="History" className="scroll-thin mt-3 flex-1 overflow-y-auto px-2 pb-3">
        {history.isPending && (
          <p className="flex items-center gap-2 px-2 py-2 text-xs text-ink-3">
            <Spinner /> Loading history…
          </p>
        )}
        {history.isError && <p className="px-2 py-2 text-xs text-bad">Could not load history.</p>}
        {history.isSuccess && !items.length && (
          <p className="px-2 py-2 text-xs text-ink-3">No requests yet. Ask your first question.</p>
        )}
        {grouped.map(([group, list]) => (
          <div key={group} className="mb-3">
            <p className="label px-2 py-1">{group}</p>
            <ul>
              {list.map((r) => (
                <li key={r.request_id}>
                  <NavLink
                    to={runLink(r)}
                    onClick={onNavigate}
                    title={r.question}
                    className={({ isActive }) =>
                      `flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] ${
                        isActive ? 'bg-well font-medium text-ink' : 'text-ink-2 hover:bg-well hover:text-ink'
                      }`
                    }
                  >
                    <Dot tone={statusTone(r.status)} pulse={r.status === 'running'} />
                    <span className="truncate">{r.question}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {isAdmin && (
          <div className="mt-2 border-t border-line pt-2">
            <NavLink
              to="/status"
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] ${
                  isActive ? 'bg-well font-medium text-ink' : 'text-ink-2 hover:bg-well hover:text-ink'
                }`
              }
            >
              <Icon name="monitor_heart" className="text-base!" /> System status
            </NavLink>
          </div>
        )}
      </nav>
      <UserCard />
    </aside>
  );
}
