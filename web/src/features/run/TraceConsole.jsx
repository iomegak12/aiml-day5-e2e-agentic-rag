import { useEffect, useRef } from 'react';

/** Agent trace (t, step, decision, detail) in a terminal-style block. */
export function TraceConsole({ trace, live = false, maxHeight = 'max-h-80' }) {
  const box = useRef(null);
  useEffect(() => {
    if (live && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [trace.length, live]);
  return (
    <div
      ref={box}
      className={`scroll-thin ${maxHeight} overflow-y-auto rounded-xl bg-code p-4 font-mono text-xs leading-6 text-code-ink`}
    >
      {trace.map((t, i) => (
        <div key={i} className="grid grid-cols-[4.5rem_9.5rem_1fr] gap-2">
          <span className="text-white/40">[{Number(t.t).toFixed(1).padStart(5, ' ')}s]</span>
          <span className="truncate font-semibold text-white">{t.step}</span>
          <span className="min-w-0 break-words text-white/75">
            {t.decision}
            {t.detail ? <span className="text-white/45"> · {t.detail}</span> : null}
          </span>
        </div>
      ))}
    </div>
  );
}
