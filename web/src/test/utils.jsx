import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { ToastProvider } from '../components/Toast';
import { AuthContext } from '../features/auth/useAuth';

export const USERS = {
  alice: { id: 'alice', name: 'Alice', role: 'guest', allowed_levels: ['public'] },
  bob: { id: 'bob', name: 'Bob', role: 'employee', allowed_levels: ['public', 'internal'] },
  carol: { id: 'carol', name: 'Carol', role: 'admin', allowed_levels: ['public', 'internal', 'restricted'] },
};

export function authValue(user = USERS.bob, overrides = {}) {
  return {
    apiKey: user ? 'k-test' : null,
    user,
    isAdmin: user?.role === 'admin',
    status: user ? 'signed-in' : 'signed-out',
    error: null,
    retry: () => {},
    signIn: async () => user,
    signOut: () => {},
    ...overrides,
  };
}

/** Render with a fresh QueryClient, a MemoryRouter and a mocked auth context. */
export function renderWithProviders(
  ui,
  { route = '/', path = '*', auth = authValue(), extraRoutes = null } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[route]}>
          <AuthContext.Provider value={auth}>
            <Routes>
              <Route path={path} element={ui} />
              {extraRoutes}
            </Routes>
          </AuthContext.Provider>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

/** A fetch Response with JSON (or problem+json) body. */
export function jsonResponse(body, { status = 200, headers = {} } = {}) {
  const type = status >= 400 ? 'application/problem+json' : 'application/json';
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': type, ...headers } });
}

/** A text/event-stream Response from [{id, event, data}] events. */
export function sseResponse(events) {
  const text = events
    .map((e) => `id: ${e.id}\nevent: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
    .join('');
  return new Response(text, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}
