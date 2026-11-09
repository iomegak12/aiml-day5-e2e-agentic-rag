import { Popover } from '../../components/Popover';
import { Icon } from '../../components/ui';
import { TIMEOUT_MAX, TIMEOUT_MIN } from './askBody';

function Toggle({ id, label, hint, checked, onChange }) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start justify-between gap-3">
      <span>
        <span className="block text-sm font-medium">{label}</span>
        <span className="block text-xs text-ink-2">{hint}</span>
      </span>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 size-4 accent-current"
      />
    </label>
  );
}

/** Request options: timeout_seconds, include_trace, bypass_cache. */
export function OptionsPopover({ value, onChange, disabled, error }) {
  const set = (patch) => onChange({ ...value, ...patch });
  const changed = value.timeout || !value.includeTrace || value.bypassCache;
  return (
    <Popover
      side="top"
      trigger={({ toggle, open }) => (
        <button
          type="button"
          onClick={toggle}
          disabled={disabled}
          aria-label="Request options"
          aria-expanded={open}
          className={`relative inline-flex size-8 items-center justify-center rounded-full bg-well hover:bg-line disabled:opacity-50 ${
            error ? 'ring-2 ring-bad' : ''
          }`}
        >
          <Icon name="tune" className="text-lg!" />
          {changed && <span className="absolute top-0 right-0 size-2 rounded-full bg-dot-info" />}
        </button>
      )}
    >
      {() => (
        <div className="w-72 space-y-4">
          <div>
            <label htmlFor="opt-timeout" className="flex items-center justify-between text-sm font-medium">
              Time budget
              <span className="font-mono text-xs text-ink-2">
                {value.timeout ? `${value.timeout} s` : 'default'}
              </span>
            </label>
            <input
              id="opt-timeout"
              type="range"
              min={0}
              max={TIMEOUT_MAX}
              step={10}
              value={value.timeout || 0}
              onChange={(e) =>
                set({ timeout: Number(e.target.value) < TIMEOUT_MIN ? null : Number(e.target.value) })
              }
              className="mt-2 w-full accent-current"
            />
            <p className="text-xs text-ink-3">
              {TIMEOUT_MIN}–{TIMEOUT_MAX} s. Slide to the left for the server default.
            </p>
            {error && <p className="mt-1 text-xs text-bad">{error}</p>}
          </div>
          <Toggle
            id="opt-trace"
            label="Include trace"
            hint="Stream trace and tool-call events (bigger responses)."
            checked={value.includeTrace}
            onChange={(v) => set({ includeTrace: v })}
          />
          <Toggle
            id="opt-cache"
            label="Bypass cache"
            hint="Skip the semantic-cache lookup and run the agent."
            checked={value.bypassCache}
            onChange={(v) => set({ bypassCache: v })}
          />
        </div>
      )}
    </Popover>
  );
}
