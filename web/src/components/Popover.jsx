import { useEffect, useRef, useState } from 'react';

/**
 * Click-to-open popover. Closes on outside click and Escape.
 * trigger: ({open, toggle}) => ReactNode, children: ({close}) => ReactNode
 */
export function Popover({
  trigger,
  children,
  align = 'left',
  side = 'bottom',
  className = '',
  wrapperClassName = 'inline-block',
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const pos = `${align === 'right' ? 'right-0' : 'left-0'} ${side === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`;
  return (
    <div ref={ref} className={`relative ${wrapperClassName}`}>
      {trigger({ open, toggle: () => setOpen((o) => !o) })}
      {open && (
        <div
          role="dialog"
          className={`absolute z-40 ${pos} min-w-56 rounded-xl border border-line bg-card p-3 shadow-lg ${className}`}
        >
          {children({ close: () => setOpen(false) })}
        </div>
      )}
    </div>
  );
}
