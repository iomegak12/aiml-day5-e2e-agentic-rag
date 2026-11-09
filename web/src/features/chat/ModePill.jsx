import { Popover } from '../../components/Popover';
import { Icon } from '../../components/ui';

const MODES = [
  {
    id: 'plan',
    label: 'Plan',
    hint: 'Plan-and-Execute: visible plan, steps run in order, re-plans on gaps.',
  },
  { id: 'react', label: 'ReAct', hint: 'Tool-routing agent: the LLM decides which search to call next.' },
];

export function ModePill({ value, onChange, disabled }) {
  const current = MODES.find((m) => m.id === value) || MODES[0];
  return (
    <Popover
      side="top"
      trigger={({ toggle, open }) => (
        <button
          type="button"
          onClick={toggle}
          disabled={disabled}
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={`Agent mode: ${current.label}`}
          className="inline-flex items-center gap-1 rounded-full bg-well px-3 py-1.5 text-sm font-medium hover:bg-line disabled:opacity-50"
        >
          {current.label}
          <Icon name="expand_more" className="text-base!" />
        </button>
      )}
    >
      {({ close }) => (
        <div role="radiogroup" aria-label="Agent mode" className="w-72 space-y-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={m.id === value}
              onClick={() => {
                onChange(m.id);
                close();
              }}
              className={`w-full rounded-lg px-3 py-2 text-left hover:bg-well ${m.id === value ? 'bg-well' : ''}`}
            >
              <span className="flex items-center justify-between text-sm font-medium">
                {m.label}
                {m.id === value && <Icon name="check" className="text-base!" />}
              </span>
              <span className="block text-xs text-ink-2">{m.hint}</span>
            </button>
          ))}
        </div>
      )}
    </Popover>
  );
}
