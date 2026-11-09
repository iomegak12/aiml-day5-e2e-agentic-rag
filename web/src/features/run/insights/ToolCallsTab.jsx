import { EmptyState, Pill } from '../../../components/ui';

/** Unified tool-call log: planner steps (plan mode) and LLM tool calls (react mode). */
export function ToolCallsTab({ toolCalls, traceIncluded = true }) {
  if (!toolCalls?.length) {
    return (
      <EmptyState icon="build" title="No tool calls">
        {traceIncluded
          ? 'The answer came without calling a tool.'
          : 'Tool calls were not requested (include_trace=false).'}
      </EmptyState>
    );
  }
  return (
    <ol className="space-y-2">
      {toolCalls.map((c) => (
        <li key={c.seq} className="rounded-lg border border-line bg-card p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <span className="font-mono text-xs text-ink-3">#{c.seq}</span>
              <span className="font-mono font-medium">{c.name}</span>
            </span>
            <span className="flex items-center gap-1">
              <Pill tone={c.origin === 'agent' ? 'info' : 'mute'}>{c.origin}</Pill>
              <Pill tone={c.status === 'ok' ? 'ok' : 'bad'}>{c.status}</Pill>
            </span>
          </div>
          {c.args && Object.keys(c.args).length > 0 && (
            <pre className="scroll-thin mt-2 overflow-x-auto rounded-md bg-well p-2 font-mono text-[11px] leading-5">
              {JSON.stringify(c.args, null, 2)}
            </pre>
          )}
          {c.result && <p className="mt-2 line-clamp-3 text-xs text-ink-2">{c.result}</p>}
          <p className="mt-1 font-mono text-[11px] text-ink-3">
            at {c.t ?? 0} s · took {c.seconds ?? 0} s
          </p>
        </li>
      ))}
    </ol>
  );
}
