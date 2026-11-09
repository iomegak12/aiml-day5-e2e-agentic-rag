import { Dot, Icon } from '../../components/ui';

const STATUSES = [
  { id: '', label: 'All' },
  { id: 'running', label: 'Running', tone: 'info' },
  { id: 'completed', label: 'Completed', tone: 'ok' },
  { id: 'client_disconnected', label: 'Disconnected', tone: 'warn' },
  { id: 'timeout', label: 'Timeout', tone: 'bad' },
  { id: 'failed', label: 'Failed', tone: 'bad' },
];

export function HistoryFilters({ text, onText, status, onStatus, mode, onMode }) {
  return (
    <div className="card flex flex-col gap-3 p-3 lg:flex-row lg:items-center">
      <label className="flex flex-1 items-center gap-2 rounded-full bg-well px-3 py-2">
        <Icon name="search" className="text-lg! text-ink-3" />
        <span className="sr-only">Search questions</span>
        <input
          type="search"
          value={text}
          onChange={(e) => onText(e.target.value)}
          placeholder="Search questions…"
          className="w-full bg-transparent text-sm outline-none placeholder:text-ink-3"
        />
      </label>
      <div role="radiogroup" aria-label="Status" className="flex flex-wrap items-center gap-1">
        {STATUSES.map((s) => (
          <button
            key={s.id || 'all'}
            type="button"
            role="radio"
            aria-checked={status === s.id}
            onClick={() => onStatus(s.id)}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm ${
              status === s.id ? 'bg-primary text-on-primary' : 'text-ink-2 hover:bg-well'
            }`}
          >
            {s.tone && <Dot tone={s.tone} />}
            {s.label}
          </button>
        ))}
      </div>
      <label className="flex items-center gap-2 rounded-full border border-line px-3 py-1 text-sm">
        Mode:
        <select
          value={mode}
          onChange={(e) => onMode(e.target.value)}
          className="bg-transparent font-semibold outline-none"
        >
          <option value="all">All</option>
          <option value="plan">Plan</option>
          <option value="react">ReAct</option>
        </select>
      </label>
    </div>
  );
}
