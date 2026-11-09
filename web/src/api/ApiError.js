import { slugOf } from '../lib/problem';

/** Error carrying an RFC 9457 problem (application/problem+json) from the API. */
export class ApiError extends Error {
  constructor(problem, { status, retryAfter = null, requestId = null } = {}) {
    super(problem?.detail || problem?.title || `HTTP ${status}`);
    this.name = 'ApiError';
    this.problem = problem || {};
    this.status = status ?? problem?.status ?? 0;
    this.slug = problem?.type ? slugOf(problem.type) : this.status ? `http-${this.status}` : 'network';
    this.retryAfter = retryAfter ?? problem?.retry_after ?? null;
    this.requestId = requestId ?? problem?.request_id ?? null;
  }

  /** Field errors of a 422 keyed by JSON pointer without the leading slash (e.g. "question"). */
  get fieldErrors() {
    const out = {};
    for (const e of this.problem.errors || []) out[(e.pointer || '').replace(/^\//, '')] = e.message;
    return out;
  }

  static async fromResponse(res) {
    let problem;
    try {
      const ct = res.headers.get('content-type') || '';
      problem = ct.includes('json') ? await res.json() : { title: res.statusText, detail: await res.text() };
    } catch {
      problem = { title: res.statusText || 'Error' };
    }
    const header = Number(res.headers.get('retry-after'));
    return new ApiError(
      { status: res.status, ...problem },
      {
        status: res.status,
        retryAfter: Number.isFinite(header) && header > 0 ? header : null,
        requestId: res.headers.get('x-request-id'),
      },
    );
  }

  static network(cause) {
    const err = new ApiError(
      { title: 'Network error', detail: cause?.message || 'Network error' },
      { status: 0 },
    );
    err.slug = 'network';
    return err;
  }
}
