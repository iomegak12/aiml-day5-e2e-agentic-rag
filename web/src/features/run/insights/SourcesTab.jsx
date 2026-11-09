import { EmptyState, Pill } from '../../../components/ui';
import { score } from '../../../lib/format';
import { sourceDomId } from '../citations';

const LEVEL_TONE = { public: 'mute', internal: 'info', restricted: 'warn' };

/** Sources behind the answer: KB article, rerank score, location, access level (RBAC) and article status. */
export function SourcesTab({ sources, highlight }) {
  if (!sources?.length) {
    return (
      <EmptyState icon="menu_book" title="No sources">
        The answer did not use knowledge-base context.
      </EmptyState>
    );
  }
  return (
    <ul className="space-y-2">
      {sources.map((s, i) => (
        <li
          key={`${s.kb_id}-${i}`}
          id={sourceDomId(s.kb_id)}
          className={`rounded-lg border border-line bg-card p-3 ${highlight === s.kb_id ? 'animate-flash' : ''}`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-sm font-semibold">{s.kb_id || 'unknown'}</span>
            <span className="flex gap-1">
              {s.access_level && <Pill tone={LEVEL_TONE[s.access_level] || 'mute'}>{s.access_level}</Pill>}
              {s.status && <Pill tone={s.status === 'current' ? 'ok' : 'warn'}>{s.status}</Pill>}
            </span>
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-ink-2">
            {s.location && <span>{s.location}</span>}
            {typeof s.score === 'number' && (
              <span className="ml-auto flex items-center gap-2">
                <span className="h-1.5 w-20 overflow-hidden rounded-full bg-well">
                  <span
                    className="block h-full bg-dot-ok"
                    style={{ width: `${Math.round(s.score * 100)}%` }}
                  />
                </span>
                <span className="font-mono">{score(s.score)}</span>
              </span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
