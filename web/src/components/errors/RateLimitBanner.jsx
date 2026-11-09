import { useEffect } from 'react';
import { useCountdown } from '../../hooks/useCountdown';
import { Icon } from '../ui';

/** 429: countdown from Retry-After (starts on mount); calls onDone when the block is over. */
export function RateLimitBanner({ retryAfter, onDone }) {
  const left = useCountdown(retryAfter || 30);
  useEffect(() => {
    if (left === 0) onDone?.();
  }, [left, onDone]);
  if (left === 0) return null;
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-3 rounded-lg border border-warn-line bg-warn-bg px-3 py-2 text-sm text-warn"
    >
      <span className="flex items-center gap-2">
        <Icon name="speed" className="text-base!" />
        <span>
          <strong>Rate limited.</strong> Too many requests from this IP. Sending is paused.
        </span>
      </span>
      <span className="flex items-center gap-1 font-mono text-xs font-semibold">
        <Icon name="progress_activity" className="animate-spin text-base!" />
        Retry in {left} s
      </span>
    </div>
  );
}
