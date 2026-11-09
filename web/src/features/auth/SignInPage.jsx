import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { RateLimitBanner } from '../../components/errors/RateLimitBanner';
import { Icon, Logo, Spinner } from '../../components/ui';
import { ThemeToggle } from '../../components/ThemeToggle';
import { useAuth } from './useAuth';

export default function SignInPage() {
  const { status, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [key, setKey] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const health = useQuery({ queryKey: keys.health, queryFn: api.health, retry: false });

  if (status === 'signed-in') return <Navigate to={location.state?.from?.pathname || '/'} replace />;

  async function onSubmit(e) {
    e.preventDefault();
    if (!key.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await signIn(key.trim());
      navigate(location.state?.from?.pathname || '/', { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const expired = location.state?.reason === 'expired' && !error;
  const rateLimited = error?.status === 429;
  const message =
    error?.status === 401
      ? 'That key is not valid. Keys are configured by your admin (API_KEYS); ask them to issue or rotate yours.'
      : error && !rateLimited
        ? error.problem?.detail || error.message
        : null;

  return (
    <main className="ambient flex min-h-full flex-col items-center justify-center px-4 py-10">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <div className="card w-full max-w-md p-8 shadow-xl shadow-black/5">
        <div className="flex flex-col items-center text-center">
          <span className="rounded-xl border border-line p-2">
            <Logo size={32} />
          </span>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight">Sign in to NetCore Assist</h1>
          <p className="mt-2 text-sm text-ink-2">
            Use your API key. Your role decides which knowledge-base articles you can see.
          </p>
        </div>

        <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
          {expired && (
            <p
              role="status"
              className="rounded-lg border border-warn-line bg-warn-bg px-3 py-2 text-sm text-warn"
            >
              Your session key is no longer valid. Please sign in again.
            </p>
          )}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label htmlFor="api-key" className="text-sm font-medium">
                API key
              </label>
              <span className="font-mono text-xs text-ink-3">X-API-KEY</span>
            </div>
            <div className="flex items-center rounded-lg border border-line bg-well focus-within:border-ink-3">
              <input
                id="api-key"
                type={show ? 'text' : 'password'}
                autoComplete="off"
                spellCheck={false}
                autoFocus
                value={key}
                onChange={(e) => setKey(e.target.value)}
                aria-invalid={Boolean(message)}
                aria-describedby={message ? 'key-error' : undefined}
                className="w-full bg-transparent px-3 py-2.5 font-mono text-sm outline-none"
                placeholder="Paste your key"
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                aria-label={show ? 'Hide key' : 'Show key'}
                className="px-3 text-ink-3 hover:text-ink"
              >
                <Icon name={show ? 'visibility_off' : 'visibility'} />
              </button>
            </div>
            {message && (
              <p id="key-error" role="alert" className="mt-2 flex items-start gap-1.5 text-sm text-bad">
                <Icon name="error" className="text-base!" /> {message}
              </p>
            )}
          </div>
          {rateLimited && <RateLimitBanner retryAfter={error.retryAfter} onDone={() => setError(null)} />}
          <button
            type="submit"
            className="btn-primary w-full rounded-lg py-2.5"
            disabled={busy || !key.trim() || rateLimited}
          >
            {busy ? <Spinner className="border-on-primary/40 border-t-on-primary" /> : null}
            Continue <Icon name="arrow_forward" className="text-base!" />
          </button>
        </form>

        <footer className="mt-6 flex items-center justify-between border-t border-line pt-4 font-mono text-xs text-ink-3">
          <span className="flex items-center gap-1">
            <Icon name="shield" className="text-sm!" /> RBAC: guest · employee · admin
          </span>
          <span>
            {health.data ? `API v${health.data.version}` : health.isError ? 'API unreachable' : '…'}
          </span>
        </footer>
      </div>
    </main>
  );
}
