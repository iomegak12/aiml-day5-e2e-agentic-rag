import { Suspense, useState } from 'react';
import { Outlet, useNavigate } from 'react-router';
import { useHotkey } from '../hooks/useHotkey';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { PageLoader } from './ui';

/** Signed-in layout: 240px sidebar + 56px header + routed content. ⌘K / Ctrl+K opens a new chat. */
export function AppShell() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  useHotkey('mod+k', () => navigate('/', { state: { fresh: Date.now() } }));

  return (
    <div className="flex h-full">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      {menuOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <Sidebar onNavigate={() => setMenuOpen(false)} />
          <button
            type="button"
            aria-label="Close menu"
            className="flex-1 bg-black/30"
            onClick={() => setMenuOpen(false)}
          />
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setMenuOpen(true)} />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <Suspense fallback={<PageLoader />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
