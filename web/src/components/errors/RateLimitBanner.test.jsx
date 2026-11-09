import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RateLimitBanner } from './RateLimitBanner';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('RateLimitBanner', () => {
  it('counts down from Retry-After and calls onDone at zero', () => {
    const onDone = vi.fn();
    render(<RateLimitBanner retryAfter={3} onDone={onDone} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Retry in 3 s');

    act(() => vi.advanceTimersByTime(1100));
    expect(screen.getByRole('alert')).toHaveTextContent('Retry in 2 s');

    act(() => vi.advanceTimersByTime(2500));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(onDone).toHaveBeenCalled();
  });
});
