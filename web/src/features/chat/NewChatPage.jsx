import { useQuery } from '@tanstack/react-query';
import { useLocation, useNavigate } from 'react-router';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { Dot, Icon } from '../../components/ui';
import { useAuth } from '../auth/useAuth';
import { Composer } from './Composer';
import { useAsk } from './useAsk';

const EXAMPLES = [
  'What does alarm NCS-BFD-3004 mean?',
  'Which QoS settings should NetCore Meet voice traffic use on SD-WAN?',
  'How do I onboard an NCX-1000 edge with zero-touch provisioning?',
  'When does an SLA breach escalate to Sev1?',
];

export default function NewChatPage() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const ask = useAsk();
  const health = useQuery({ queryKey: keys.health, queryFn: api.health, retry: false });
  const prefill = location.state || {};
  // Remount the composer for ⌘K / "New chat" / "Ask again" / example clicks.
  const composerKey = `${location.key}-${prefill.fresh || ''}-${prefill.question || ''}`;

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 py-6 sm:px-6">
      <div className="flex items-center justify-between text-xs">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-well px-3 py-1 font-medium text-ink-2">
          <Dot tone="ok" />
          Signed in as {user.name} · sees {user.allowed_levels.join(' + ')} articles
        </span>
        <span className="font-mono text-ink-3">{health.data ? `API v${health.data.version}` : ''}</span>
      </div>

      <div className="flex flex-1 flex-col justify-center py-10">
        <h1 className="text-center text-3xl font-semibold tracking-tight sm:text-4xl">
          What can I help with?
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-center text-ink-2">
          Answers from the NetCore knowledge base (SD-WAN, Meet and Calling) with a visible plan, sources and
          a quality judge.
        </p>
        <div className="mt-8">
          <Composer
            key={composerKey}
            initial={prefill}
            onSubmit={ask.submit}
            pending={ask.pending}
            error={ask.error}
            onClearError={ask.clearError}
            autoFocus
          />
          <p className="mt-2 text-center text-xs text-ink-3">AI-generated, for reference only</p>
        </div>
      </div>

      <section aria-labelledby="examples" className="pb-4">
        <h2 id="examples" className="label mb-3 text-center">
          Examples of queries
        </h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {EXAMPLES.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => navigate('/', { state: { question: q, fresh: Date.now() } })}
              disabled={ask.pending}
              className="flex items-center justify-between gap-2 rounded-full border border-line bg-card px-4 py-2.5 text-left text-sm hover:bg-well disabled:opacity-50"
            >
              <span className="truncate">{q}</span>
              <Icon name="chevron_right" className="text-base! text-ink-3" />
            </button>
          ))}
        </div>
        <p className="mt-6 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 font-mono text-[11px] text-ink-3">
          <span>POST /api/v1/agent/ask/stream</span>
          <span>·</span>
          <span>rate limit 100 req/min per IP</span>
          <span>·</span>
          <span>X-API-Key: ••••••••</span>
        </p>
      </section>
    </div>
  );
}
