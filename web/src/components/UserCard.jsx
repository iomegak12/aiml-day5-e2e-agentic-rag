import { useAuth } from '../features/auth/useAuth';
import { capitalize } from '../lib/format';
import { Popover } from './Popover';
import { Avatar, Icon, Pill } from './ui';

const ROLE_TONE = { guest: 'mute', employee: 'info', admin: 'ok' };

export function UserCard() {
  const { user, signOut } = useAuth();
  if (!user) return null;
  return (
    <div className="border-t border-line p-2">
      <Popover
        side="top"
        wrapperClassName="block w-full"
        trigger={({ toggle }) => (
          <button
            type="button"
            onClick={toggle}
            className="flex w-full items-center gap-2.5 rounded-lg border border-line bg-card px-2.5 py-2 text-left hover:bg-well"
          >
            <Avatar name={user.name} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{user.name}</span>
              <span className="block truncate text-xs text-ink-3">{user.allowed_levels.join(' + ')}</span>
            </span>
            <Pill tone={ROLE_TONE[user.role] || 'mute'}>{capitalize(user.role)}</Pill>
          </button>
        )}
      >
        {({ close }) => (
          <div className="w-52 space-y-2 text-sm">
            <p className="text-ink-2">
              Signed in as <strong className="text-ink">{user.name}</strong> ({user.role}). You can see{' '}
              {user.allowed_levels.join(', ')} articles.
            </p>
            <button
              type="button"
              onClick={() => {
                close();
                signOut();
              }}
              className="btn-ghost w-full"
            >
              <Icon name="logout" className="text-base!" /> Sign out
            </button>
          </div>
        )}
      </Popover>
    </div>
  );
}
