import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { Icon } from './ui';

const ToastContext = createContext(() => {});

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const seq = useRef(0);
  const show = useCallback((message, { icon = 'check_circle', ms = 2200 } = {}) => {
    const id = ++seq.current;
    setToasts((t) => [...t, { id, message, icon }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), ms);
  }, []);
  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed right-4 bottom-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm text-on-primary shadow-lg"
          >
            <Icon name={t.icon} className="text-base!" />
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => useContext(ToastContext);

/** Copy text to the clipboard and confirm with a toast. */
export function CopyButton({ text, label = 'Copy', className = '', iconOnly = false }) {
  const toast = useToast();
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      toast('Copied to clipboard');
    } catch {
      toast('Copy failed', { icon: 'error' });
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={label}
      title={label}
      className={`inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs font-medium text-ink-2 hover:bg-well hover:text-ink ${className}`}
    >
      <Icon name="content_copy" className="text-base!" />
      {!iconOnly && label}
    </button>
  );
}
