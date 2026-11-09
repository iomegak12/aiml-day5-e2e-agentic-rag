import { afterEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse } from '../test/utils';
import { ApiError } from './ApiError';
import { apiFetch, setUnauthorizedHandler } from './client';

const problem = (slug, status, extra = {}) => ({
  type: `https://netcore.example/problems/${slug}`,
  title: slug,
  status,
  request_id: 'req-1',
  ...extra,
});

afterEach(() => vi.unstubAllGlobals());

describe('apiFetch', () => {
  it('sends the X-API-Key from sessionStorage and parses JSON', async () => {
    sessionStorage.setItem('nc-api-key', 'k-bob');
    const fetch = vi.fn().mockResolvedValue(jsonResponse({ id: 'bob' }));
    vi.stubGlobal('fetch', fetch);
    await expect(apiFetch('/api/v1/me')).resolves.toEqual({ id: 'bob' });
    expect(fetch.mock.calls[0][1].headers['X-API-Key']).toBe('k-bob');
  });

  it('turns application/problem+json into an ApiError with slug, retryAfter and request id', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(problem('rate-limited', 429, { retry_after: 30 }), {
          status: 429,
          headers: { 'Retry-After': '17' },
        }),
      ),
    );
    const err = await apiFetch('/api/v1/agent/requests').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
    expect(err.slug).toBe('rate-limited');
    expect(err.retryAfter).toBe(17); // header wins over the body extension
    expect(err.requestId).toBe('req-1');
  });

  it('maps 422 errors to field errors by JSON pointer', async () => {
    const body = problem('validation-error', 422, {
      errors: [{ pointer: '/timeout_seconds', location: 'body', message: 'must be between 10 and 300' }],
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(body, { status: 422 })));
    const err = await apiFetch('/x', { method: 'POST', body: {} }).catch((e) => e);
    expect(err.fieldErrors).toEqual({ timeout_seconds: 'must be between 10 and 300' });
  });

  it('notifies the unauthorized handler on 401 (signs out)', async () => {
    const handler = vi.fn();
    const off = setUnauthorizedHandler(handler);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(problem('unauthorized', 401), { status: 401 })),
    );
    await expect(apiFetch('/api/v1/agent/requests')).rejects.toMatchObject({ status: 401 });
    expect(handler).toHaveBeenCalledOnce();
    off();
  });

  it('does not sign out when an explicit key (sign-in attempt) is rejected', async () => {
    const handler = vi.fn();
    const off = setUnauthorizedHandler(handler);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(problem('unauthorized', 401), { status: 401 })),
    );
    await expect(apiFetch('/api/v1/me', { apiKey: 'wrong' })).rejects.toMatchObject({ status: 401 });
    expect(handler).not.toHaveBeenCalled();
    off();
  });

  it('reports network failures as slug "network"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const err = await apiFetch('/health', { auth: false }).catch((e) => e);
    expect(err.slug).toBe('network');
    expect(err.status).toBe(0);
  });
});
