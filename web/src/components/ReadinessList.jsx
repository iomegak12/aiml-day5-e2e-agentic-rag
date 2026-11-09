import { Icon, Pill } from './ui';

const SUBSYSTEMS = {
  chroma: { label: 'Chroma vector DB', icon: 'hub' },
  redis: { label: 'Redis cache and event buffer', icon: 'memory' },
  postgres: { label: 'Postgres audit DB', icon: 'database' },
};

/** /ready checks: {chroma|redis|postgres: {status: "up"|"down", ms, error?}} */
export function ReadinessList({ checks }) {
  if (!checks) return null;
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-card">
      {Object.entries(checks).map(([name, c]) => {
        const meta = SUBSYSTEMS[name] || { label: name, icon: 'dns' };
        const up = c.status === 'up';
        return (
          <li key={name} className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
            <span className="flex items-center gap-2">
              <Icon name={meta.icon} className="text-lg! text-ink-2" />
              {meta.label}
            </span>
            <span className="flex items-center gap-2">
              {c.error && (
                <span className="hidden max-w-60 truncate text-xs text-ink-3 sm:inline">{c.error}</span>
              )}
              <Pill tone={up ? 'ok' : 'bad'}>
                {up ? '✓ Healthy' : '✕ Unreachable'}
                {typeof c.ms === 'number' && ` (${c.ms} ms)`}
              </Pill>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
