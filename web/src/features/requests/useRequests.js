import { useInfiniteQuery } from '@tanstack/react-query';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';

/** Cursor-paginated GET /api/v1/agent/requests (status filter is server-side). */
export function useRequests({ status, limit = 20 } = {}) {
  const query = useInfiniteQuery({
    queryKey: keys.requests({ status: status || 'all', limit }),
    queryFn: ({ pageParam }) => api.listRequests({ status, limit, cursor: pageParam }),
    initialPageParam: undefined,
    getNextPageParam: (last) => last.next_cursor || undefined,
    refetchInterval: (q) =>
      q.state.data?.pages.some((p) => p.items.some((r) => r.status === 'running')) ? 5_000 : false,
  });
  const items = query.data?.pages.flatMap((p) => p.items) || [];
  return { ...query, items };
}

/** Client-side text + mode filters over the loaded page(s). */
export function filterRuns(items, { text = '', mode = 'all' } = {}) {
  const needle = text.trim().toLowerCase();
  return items.filter(
    (r) => (mode === 'all' || r.mode === mode) && (!needle || r.question.toLowerCase().includes(needle)),
  );
}

/** Header stats over the loaded runs: average latency and cache-hit rate. */
export function runStats(items) {
  const timed = items.filter((r) => typeof r.elapsed_s === 'number');
  const finished = items.filter((r) => r.agent_status);
  return {
    avgLatency: timed.length ? timed.reduce((a, r) => a + r.elapsed_s, 0) / timed.length : null,
    cacheHitRate: finished.length
      ? finished.filter((r) => r.agent_status === 'cache_hit').length / finished.length
      : null,
  };
}
