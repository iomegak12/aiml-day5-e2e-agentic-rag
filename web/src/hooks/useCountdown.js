import { useEffect, useState } from 'react';

/** Seconds left of a countdown that starts when the component mounts (remount it to restart). */
export function useCountdown(seconds) {
  const [end] = useState(() => Date.now() + (seconds || 0) * 1000);
  const [left, setLeft] = useState(seconds || 0);
  const running = left > 0;
  useEffect(() => {
    if (!running) return undefined;
    const timer = setInterval(() => setLeft(Math.max(0, Math.ceil((end - Date.now()) / 1000))), 250);
    return () => clearInterval(timer);
  }, [end, running]);
  return left;
}

/** Seconds elapsed since `since` (ms), ticking every second while `running`. */
export function useElapsed(since, running) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);
  return since ? Math.max(0, (now - since) / 1000) : 0;
}
