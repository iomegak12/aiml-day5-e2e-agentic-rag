import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { setUnauthorizedHandler } from '../../api/client';
import { api } from '../../api/endpoints';
import { keys } from '../../api/queryClient';
import { clearApiKey, getApiKey, setApiKey } from '../../lib/storage';
import { resetRuns } from '../run/runStore';
import { AuthContext } from './useAuth';

/**
 * Holds the X-API-Key (sessionStorage) and the profile from GET /api/v1/me.
 * Any 401 from any call signs the user out and returns to /sign-in.
 */
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [apiKey, setKey] = useState(() => getApiKey());

  const me = useQuery({
    queryKey: keys.me(apiKey),
    queryFn: () => api.me(),
    enabled: Boolean(apiKey),
    staleTime: Infinity,
  });

  const signIn = useCallback(
    async (key) => {
      const user = await api.me(key); // throws ApiError(401) for a bad key; nothing is stored then
      setApiKey(key);
      queryClient.setQueryData(keys.me(key), user);
      setKey(key);
      return user;
    },
    [queryClient],
  );

  const signOut = useCallback(
    (reason) => {
      clearApiKey();
      resetRuns();
      queryClient.clear();
      setKey(null);
      navigate('/sign-in', { replace: true, state: reason ? { reason } : undefined });
    },
    [navigate, queryClient],
  );

  useEffect(() => setUnauthorizedHandler(() => signOut('expired')), [signOut]);

  const value = useMemo(
    () => ({
      apiKey,
      user: me.data || null,
      isAdmin: me.data?.role === 'admin',
      status: !apiKey ? 'signed-out' : me.isPending ? 'loading' : me.isError ? 'error' : 'signed-in',
      error: me.error,
      retry: me.refetch,
      signIn,
      signOut,
    }),
    [apiKey, me.data, me.isPending, me.isError, me.error, me.refetch, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
