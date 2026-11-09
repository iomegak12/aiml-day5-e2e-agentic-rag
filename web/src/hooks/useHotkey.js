import { useEffect, useRef } from 'react';

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '');
export const MOD_LABEL = isMac ? '⌘' : 'Ctrl';

/** useHotkey('mod+k', handler): "mod" is ⌘ on macOS and Ctrl elsewhere. */
export function useHotkey(combo, handler) {
  const ref = useRef(handler);
  useEffect(() => {
    ref.current = handler;
  });
  useEffect(() => {
    const parts = combo.toLowerCase().split('+');
    const key = parts.pop();
    const wantMod = parts.includes('mod');
    const wantShift = parts.includes('shift');
    function onKey(e) {
      const mod = isMac ? e.metaKey : e.ctrlKey;
      if (e.key.toLowerCase() === key && mod === wantMod && e.shiftKey === wantShift) {
        e.preventDefault();
        ref.current(e);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [combo]);
}
