import { createContext, useContext } from 'react';

export const AuthContext = createContext(null);

/** {apiKey, user, isAdmin, status, error, retry, signIn(key), signOut(reason?)} */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
