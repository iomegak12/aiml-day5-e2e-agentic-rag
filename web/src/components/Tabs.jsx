import { useId } from 'react';

/** Accessible tab strip (roving arrow keys). tabs: [{id, label, count?}] */
export function Tabs({ tabs, value, onChange, className = '' }) {
  const base = useId();
  function onKeyDown(e) {
    const i = tabs.findIndex((t) => t.id === value);
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      onChange(next.id);
      document.getElementById(`${base}-${next.id}`)?.focus();
    }
  }
  return (
    <div role="tablist" className={`flex gap-1 rounded-lg bg-well p-1 ${className}`} onKeyDown={onKeyDown}>
      {tabs.map((t) => {
        const active = t.id === value;
        return (
          <button
            key={t.id}
            id={`${base}-${t.id}`}
            role="tab"
            type="button"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(t.id)}
            className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium whitespace-nowrap transition ${
              active ? 'bg-card text-ink shadow-sm' : 'text-ink-2 hover:text-ink'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-ink-3">{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
