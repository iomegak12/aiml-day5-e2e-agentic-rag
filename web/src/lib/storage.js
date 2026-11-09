// Browser storage helpers. Every access is guarded: private mode or blocked storage must not break the app.
const KEY = 'nc-api-key';
const THEME = 'nc-theme';

function safe(fn, fallback = null) {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

/** The API key lives in sessionStorage: survives a refresh, cleared when the tab closes. */
export const getApiKey = () => safe(() => sessionStorage.getItem(KEY));
export const setApiKey = (value) => safe(() => sessionStorage.setItem(KEY, value));
export const clearApiKey = () => safe(() => sessionStorage.removeItem(KEY));

export const getStoredTheme = () => safe(() => localStorage.getItem(THEME));
export const setStoredTheme = (value) => safe(() => localStorage.setItem(THEME, value));
