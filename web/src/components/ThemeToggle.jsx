import { useTheme } from '../hooks/useTheme';
import { Icon } from './ui';

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className="inline-flex size-8 items-center justify-center rounded-full text-ink-2 hover:bg-well hover:text-ink"
    >
      <Icon name={theme === 'dark' ? 'light_mode' : 'dark_mode'} />
    </button>
  );
}
