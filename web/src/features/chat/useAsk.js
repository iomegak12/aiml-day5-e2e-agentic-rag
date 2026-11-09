import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router';
import { startAsk } from '../run/runStore';

/** Start a streamed run and open its live view. Exposes the ApiError when the run was not accepted. */
export function useAsk() {
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const submit = useCallback(
    async (body) => {
      setPending(true);
      setError(null);
      try {
        const id = await startAsk(body);
        navigate(`/runs/${id}/live`);
        return id;
      } catch (err) {
        setError(err);
        return null;
      } finally {
        setPending(false);
      }
    },
    [navigate],
  );

  return { submit, pending, error, clearError: useCallback(() => setError(null), []) };
}
