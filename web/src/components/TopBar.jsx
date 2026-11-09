import { useQuery } from '@tanstack/react-query';
import { NavLink } from 'react-router';
import { api } from '../api/endpoints';
import { keys } from '../api/queryClient';
import { MOD_LABEL } from '../hooks/useHotkey';
import { Popover } from './Popover';
import { ThemeToggle } from './ThemeToggle';
import { Dot, Icon, Kbd } from './ui';

const navCls = ({ isActive }) =>
  `rounded-md px-2 py-1 text-sm transition ${isActive ? 'font-semibold text-ink' : 'text-ink-2 hover:text-ink'}`;

/** Liveness of the API through the gateway (GET /health every 30 s; it is not rate limited). */
function ApiStatusPill() {
  const health = useQuery({
    queryKey: keys.health,
    queryFn: api.health,
    refetchInterval: 30_000,
    retry: false,
  });
  const ok = health.isSuccess;
  return (
    <span
      className="hidden items-center gap-1.5 rounded-full border border-line bg-card px-2.5 py-1 text-xs font-medium sm:inline-flex"
      title={ok ? `API v${health.data.version}` : 'GET /health failed'}
    >
      <Dot tone={health.isPending ? 'mute' : ok ? 'ok' : 'bad'} />
      API: {health.isPending ? 'checking' : ok ? 'connected' : 'unreachable'}
    </span>
  );
}

function Help() {
  return (
    <Popover
      align="right"
      trigger={({ toggle }) => (
        <button
          type="button"
          onClick={toggle}
          aria-label="Help"
          className="inline-flex size-8 items-center justify-center rounded-full text-ink-2 hover:bg-well hover:text-ink"
        >
          <Icon name="help" />
        </button>
      )}
    >
      {() => (
        <div className="w-64 space-y-2 text-sm">
          <p className="font-semibold">Keyboard shortcuts</p>
          <ul className="space-y-1.5 text-ink-2">
            <li className="flex justify-between">
              New chat
              <span>
                <Kbd>{MOD_LABEL}</Kbd> <Kbd>K</Kbd>
              </span>
            </li>
            <li className="flex justify-between">
              Send question <Kbd>Enter</Kbd>
            </li>
            <li className="flex justify-between">
              New line
              <span>
                <Kbd>Shift</Kbd> <Kbd>Enter</Kbd>
              </span>
            </li>
          </ul>
          <p className="border-t border-line pt-2 text-xs text-ink-3">
            Answers are AI-generated from the NetCore knowledge base; check the cited sources.
          </p>
        </div>
      )}
    </Popover>
  );
}

export function TopBar({ onMenu }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line bg-canvas/80 px-4 backdrop-blur">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onMenu}
          aria-label="Open menu"
          className="inline-flex size-8 items-center justify-center rounded-md text-ink-2 hover:bg-well md:hidden"
        >
          <Icon name="menu" />
        </button>
        <nav aria-label="Main" className="flex items-center gap-1">
          <NavLink to="/" end className={navCls}>
            Chat
          </NavLink>
          <NavLink to="/requests" className={navCls}>
            Requests
          </NavLink>
        </nav>
      </div>
      <div className="flex items-center gap-1.5">
        <ApiStatusPill />
        <ThemeToggle />
        <Help />
      </div>
    </header>
  );
}
