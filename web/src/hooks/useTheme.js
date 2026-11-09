import { useCallback, useSyncExternalStore } from 'react';
import { getStoredTheme, setStoredTheme } from '../lib/storage';

// Theme = the "dark" class on <html>. First visit follows prefers-color-scheme; a toggle is remembered.
const listeners = new Set();

export function initialTheme() {
  const stored = getStoredTheme();
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  listeners.forEach((fn) => fn());
}

const current = () => (document.documentElement.classList.contains('dark') ? 'dark' : 'light');

export function useTheme() {
  const theme = useSyncExternalStore((fn) => {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }, current);
  const toggle = useCallback(() => {
    const next = current() === 'dark' ? 'light' : 'dark';
    setStoredTheme(next);
    applyTheme(next);
  }, []);
  return { theme, toggle };
}
