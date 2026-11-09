import { CopyButton } from '../Toast';
import { Icon } from '../ui';

/** Collapsible RFC 9457 problem details (application/problem+json). */
export function ProblemPanel({ problem, defaultOpen = false }) {
  if (!problem) return null;
  const json = JSON.stringify(problem, null, 2);
  return (
    <details open={defaultOpen} className="group rounded-lg border border-line bg-well">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-sm font-medium">
        <span className="flex items-center gap-1.5">
          <Icon name="chevron_right" className="text-base! transition group-open:rotate-90" />
          Problem details (RFC 9457)
        </span>
        <span className="font-mono text-xs text-ink-3">application/problem+json</span>
      </summary>
      <div className="relative px-3 pb-3">
        <CopyButton text={json} className="absolute top-2 right-5 bg-card" />
        <pre className="scroll-thin overflow-x-auto rounded-md bg-code p-3 font-mono text-xs leading-5 text-code-ink">
          {json}
        </pre>
      </div>
    </details>
  );
}
