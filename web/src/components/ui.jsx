// Small presentational primitives shared by every feature.

/** Material Symbols icon (self-hosted font, ligature name). */
export function Icon({ name, className = '', filled = false, ...rest }) {
  return (
    <span aria-hidden="true" className={`icon ${className}`} data-filled={filled || undefined} {...rest}>
      {name}
    </span>
  );
}

export function Logo({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="NetCore Assist">
      <rect width="32" height="32" rx="8" fill="#111111" />
      <path
        d="M10 21.5 16 10.5l6 11M10 21.5h12"
        fill="none"
        stroke="#ffffff"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity=".55"
      />
      <circle cx="16" cy="10.5" r="3" fill="#ffffff" />
      <circle cx="10" cy="21.5" r="3" fill="#ffffff" />
      <circle cx="22" cy="21.5" r="3" fill="#FDE68A" />
    </svg>
  );
}

export function Spinner({ className = '' }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block size-4 animate-spin rounded-full border-2 border-line-strong border-t-ink ${className}`}
    />
  );
}

export function PageLoader({ label = 'Loading…' }) {
  return (
    <div className="flex h-full min-h-40 items-center justify-center gap-3 text-sm text-ink-2">
      <Spinner /> {label}
    </div>
  );
}

const TONES = {
  ok: 'bg-ok-bg text-ok border-ok-line',
  warn: 'bg-warn-bg text-warn border-warn-line',
  bad: 'bg-bad-bg text-bad border-bad-line',
  info: 'bg-info-bg text-info border-info-line',
  mute: 'bg-mute-bg text-mute border-mute-line',
};
const DOTS = {
  ok: 'bg-dot-ok',
  warn: 'bg-dot-warn',
  bad: 'bg-dot-bad',
  info: 'bg-dot-info',
  mute: 'bg-dot-mute',
};

export function Dot({ tone = 'mute', pulse = false, className = '' }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block size-2 shrink-0 rounded-full ${DOTS[tone]} ${pulse ? 'animate-pulse-dot' : ''} ${className}`}
    />
  );
}

export function Pill({ tone = 'mute', dot = false, pulse = false, children, className = '' }) {
  return (
    <span className={`chip border ${TONES[tone]} ${className}`}>
      {dot && <Dot tone={tone} pulse={pulse} />}
      {children}
    </span>
  );
}

export function Kbd({ children }) {
  return <kbd className="kbd">{children}</kbd>;
}

export function Card({ className = '', children, ...rest }) {
  return (
    <section className={`card ${className}`} {...rest}>
      {children}
    </section>
  );
}

export function EmptyState({ icon = 'inbox', title, children }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-sm text-ink-2">
      <Icon name={icon} className="text-3xl! text-ink-3" />
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="max-w-md">{children}</div>}
    </div>
  );
}

export function Avatar({ name = '?', size = 'md' }) {
  const cls = size === 'sm' ? 'size-6 text-[11px]' : 'size-8 text-sm';
  return (
    <span
      aria-hidden="true"
      className={`inline-flex ${cls} shrink-0 items-center justify-center rounded-full bg-primary font-semibold text-on-primary`}
    >
      {name.trim().charAt(0).toUpperCase() || '?'}
    </span>
  );
}
