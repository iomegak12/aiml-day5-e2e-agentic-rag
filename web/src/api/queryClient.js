import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './ApiError';

const NO_RETRY = new Set([400, 401, 403, 404, 422, 429]);

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
      retry: (count, error) => !(error instanceof ApiError && NO_RETRY.has(error.status)) && count < 2,
    },
  },
});

export const keys = {
  me: (key) => ['me', key],
  requests: (filters = {}) => ['requests', filters],
  request: (id) => ['request', id],
  health: ['health'],
  ready: ['ready'],
};
