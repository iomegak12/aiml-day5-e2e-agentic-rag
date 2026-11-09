import { screen } from '@testing-library/react';
import { Route } from 'react-router';
import { describe, expect, it } from 'vitest';
import { authValue, renderWithProviders, USERS } from '../../test/utils';
import { RequireAdmin, RequireAuth } from './guards';

describe('route guards', () => {
  it('RequireAdmin hides the page from non-admins', () => {
    renderWithProviders(
      <RequireAdmin>
        <p>secret status</p>
      </RequireAdmin>,
      { auth: authValue(USERS.bob) },
    );
    expect(screen.getByRole('heading', { name: 'Admins only' })).toBeInTheDocument();
    expect(screen.queryByText('secret status')).not.toBeInTheDocument();
  });

  it('RequireAdmin renders the page for admins', () => {
    renderWithProviders(
      <RequireAdmin>
        <p>secret status</p>
      </RequireAdmin>,
      { auth: authValue(USERS.carol) },
    );
    expect(screen.getByText('secret status')).toBeInTheDocument();
  });

  it('RequireAuth redirects signed-out users to /sign-in', () => {
    renderWithProviders(<RequireAuth />, {
      route: '/requests',
      path: '/requests',
      auth: authValue(null),
      extraRoutes: <Route path="/sign-in" element={<p>sign-in form</p>} />,
    });
    expect(screen.getByText('sign-in form')).toBeInTheDocument();
  });
});
