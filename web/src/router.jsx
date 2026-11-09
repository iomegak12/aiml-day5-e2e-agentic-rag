import { lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router';
import { AppShell } from './components/AppShell';
import { RequireAuth } from './features/auth/guards';
import SignInPage from './features/auth/SignInPage';

// Feature screens are code-split; the shell and sign-in load with the first bundle.
const NewChatPage = lazy(() => import('./features/chat/NewChatPage'));
const LiveRunPage = lazy(() => import('./features/run/LiveRunPage'));
const AnswerPage = lazy(() => import('./features/run/AnswerPage'));
const HistoryPage = lazy(() => import('./features/requests/HistoryPage'));
const RequestDetailPage = lazy(() => import('./features/requests/RequestDetailPage'));
const SystemStatusPage = lazy(() => import('./features/status/SystemStatusPage'));

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<NewChatPage />} />
          <Route path="runs/:id/live" element={<LiveRunPage />} />
          <Route path="runs/:id" element={<AnswerPage />} />
          <Route path="requests" element={<HistoryPage />} />
          <Route path="requests/:id" element={<RequestDetailPage />} />
          <Route path="status" element={<SystemStatusPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
