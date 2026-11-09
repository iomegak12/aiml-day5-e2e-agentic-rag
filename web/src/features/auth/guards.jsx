import { Link, Navigate, Outlet, useLocation } from 'react-router';
import { ErrorView } from '../../components/errors/ErrorCards';
import { PageLoader } from '../../components/ui';
import { useAuth } from './useAuth';

/** Routes below need a key and a loaded profile. */
export function RequireAuth() {
  const { status, error, retry } = useAuth();
  const location = useLocation();
  if (status === 'signed-out') return <Navigate to="/sign-in" replace state={{ from: location }} />;
  if (status === 'loading') return <PageLoader label="Checking your key…" />;
  if (status === 'error')
    return (
      <div className="mx-auto max-w-lg p-8">
        <ErrorView error={error} onRetry={retry} />
      </div>
    );
  return <Outlet />;
}

/** Admin-only routes (System status). Non-admins see an explanation instead of a 403 page. */
export function RequireAdmin({ children }) {
  const { isAdmin } = useAuth();
  if (isAdmin) return children;
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="card max-w-md p-8 text-center shadow-sm">
        <h2 className="text-xl font-semibold">Admins only</h2>
        <p className="mt-2 text-sm text-ink-2">
          System status is shown to admins. The API&apos;s <code className="font-mono">/health</code> and{' '}
          <code className="font-mono">/ready</code> are operational probes; the UI hides this page from other
          roles.
        </p>
        <Link to="/" className="btn-primary mt-5">
          Back to chat
        </Link>
      </div>
    </div>
  );
}
