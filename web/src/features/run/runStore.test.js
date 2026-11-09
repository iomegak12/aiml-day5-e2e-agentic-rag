import { afterEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse, sseResponse } from '../../test/utils';
import { attach, detach, getRun, resetRuns, startAsk } from './runStore';

afterEach(() => {
  resetRuns();
  vi.unstubAllGlobals();
});

const until = async (fn) => vi.waitFor(() => expect(fn()).toBeTruthy());

describe('runStore', () => {
  it('startAsk POSTs the question, resolves with the request id and keeps streaming', async () => {
    sessionStorage.setItem('nc-api-key', 'k-bob');
    const fetch = vi.fn().mockResolvedValue(
      sseResponse([
        {
          id: '1-0',
          event: 'accepted',
          data: { request_id: 'r1', user: { id: 'bob', role: 'employee' }, options: { mode: 'plan' } },
        },
        {
          id: '2-0',
          event: 'result',
          data: { agent_status: 'answered', question: 'What is BFD?', answer: 'x' },
        },
        { id: '3-0', event: 'done', data: { request_id: 'r1', status: 'completed' } },
      ]),
    );
    vi.stubGlobal('fetch', fetch);

    await expect(startAsk({ question: 'What is BFD?', mode: 'plan' })).resolves.toBe('r1');
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe('/api/v1/agent/ask/stream');
    expect(init.method).toBe('POST');
    expect(init.headers['X-API-Key']).toBe('k-bob');
    expect(JSON.parse(init.body)).toEqual({ question: 'What is BFD?', mode: 'plan' });

    await until(() => getRun('r1')?.phase === 'done');
    expect(getRun('r1').result.agent_status).toBe('answered');
  });

  it('startAsk rejects with the problem when the run is not accepted (429)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { type: 'https://netcore.example/problems/rate-limited', title: 'Too many requests', status: 429 },
          {
            status: 429,
            headers: { 'Retry-After': '30' },
          },
        ),
      ),
    );
    await expect(startAsk({ question: 'hello', mode: 'plan' })).rejects.toMatchObject({
      status: 429,
      retryAfter: 30,
    });
  });

  it('attach resumes with Last-Event-ID after detach and marks missed events as replayed', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        sseResponse([{ id: '1-0', event: 'accepted', data: { request_id: 'r2', options: {} } }]),
      )
      .mockResolvedValueOnce(
        sseResponse([
          { id: '2-0', event: 'step', data: { id: 1, version: 1, status: 'done' } },
          { id: '3-0', event: 'done', data: { request_id: 'r2', status: 'completed' } },
        ]),
      );
    vi.stubGlobal('fetch', fetch);

    attach('r2'); // fresh attach: no Last-Event-ID
    await until(() => getRun('r2')?.events.length === 1);
    detach('r2');
    expect(getRun('r2').phase).toBe('detached');

    attach('r2'); // resume
    await until(() => getRun('r2')?.phase === 'done');
    expect(fetch.mock.calls[0][1].headers['Last-Event-ID']).toBeUndefined();
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/agent/requests/r2/events');
    expect(fetch.mock.calls[1][1].headers['Last-Event-ID']).toBe('1-0');
    expect(getRun('r2').replayedCount).toBe(2); // ids 2-0 / 3-0 are older than the resume time
  });
});
