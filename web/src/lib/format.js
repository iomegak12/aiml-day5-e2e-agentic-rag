// Small, dependency-free formatters used across features.

export function formatSeconds(s) {
  if (s === null || s === undefined || Number.isNaN(Number(s))) return '–';
  const n = Number(s);
  if (n < 60) return `${n.toFixed(n < 10 ? 1 : 0)} s`;
  const m = Math.floor(n / 60);
  return `${m}m ${Math.round(n - m * 60)}s`;
}

export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

export function formatTime(iso) {
  if (!iso) return '–';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '–' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatDateTime(iso) {
  if (!iso) return '–';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? '–'
    : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/** 'Today' | 'Yesterday' | 'Earlier' for the sidebar history groups. */
export function dayGroup(iso, now = new Date()) {
  if (!iso) return 'Earlier';
  const d = new Date(iso);
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (d >= start) return 'Today';
  if (d >= new Date(start.getTime() - 86_400_000)) return 'Yesterday';
  return 'Earlier';
}

export const shortId = (id = '') => (id.length > 12 ? `${id.slice(0, 8)}…` : id);
export const initials = (name = '?') => name.trim().charAt(0).toUpperCase() || '?';
export const capitalize = (s = '') => s.charAt(0).toUpperCase() + s.slice(1);
export const score = (n) => (typeof n === 'number' ? n.toFixed(2) : '–');

/** Redis Stream ids are "<ms>-<seq>"; Postgres replays use "db-N" (no time). */
export function eventTimeMs(id) {
  const m = /^(\d+)-\d+$/.exec(id || '');
  return m ? Number(m[1]) : null;
}
