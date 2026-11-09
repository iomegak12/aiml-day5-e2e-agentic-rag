import { useEffect, useRef } from 'react';
import { EmptyState } from '../../components/ui';
import { eventTone, summarizeEvent } from './eventSummary';

const CHIP = {
  ok: 'bg-ok-bg text-ok',
  warn: 'bg-warn-bg text-warn',
  bad: 'bg-bad-bg text-bad',
  info: 'bg-well text-ink',
  mute: 'bg-well text-ink-2',
};

/** Raw SSE events as they arrive: id, event type and a one-line summary. Auto-scrolls while live. */
export function EventLog({ events, live = false }) {
  const end = useRef(null);
  useEffect(() => {
    if (live) end.current?.scrollIntoView({ block: 'nearest' });
  }, [events.length, live]);
  if (!events.length) return <EmptyState icon="stream" title="Waiting for events…" />;
  return (
    <ol className="divide-y divide-line text-[13px]">
      {events.map((e, i) => (
        <li key={e.id || i} className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 py-2.5">
          <span className="font-mono text-[11px] text-ink-3">{e.id || '–'}</span>
          <span />
          <span
            className={`h-fit rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${CHIP[eventTone(e.event, e.data)]}`}
          >
            {e.event}
          </span>
          <span className="min-w-0 break-words text-ink-2">{summarizeEvent(e)}</span>
        </li>
      ))}
      <li ref={end} aria-hidden="true" />
    </ol>
  );
}
