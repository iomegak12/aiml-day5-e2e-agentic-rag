import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../api/ApiError';
import { authValue, jsonResponse, renderWithProviders, USERS } from '../../test/utils';
import SignInPage from './SignInPage';

afterEach(() => vi.unstubAllGlobals());

function setup(signIn) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'ok', version: '0.8.0' })));
  return renderWithProviders(<SignInPage />, {
    route: '/sign-in',
    path: '/sign-in',
    auth: authValue(null, { signIn }),
    extraRoutes: <Route path="/" element={<p>chat home</p>} />,
  });
}

describe('SignInPage', () => {
  it('signs in with a valid key and opens the chat', async () => {
    const signIn = vi.fn().mockResolvedValue(USERS.bob);
    setup(signIn);
    await userEvent.type(screen.getByLabelText('API key'), '  k-bob  ');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(signIn).toHaveBeenCalledWith('k-bob');
    expect(await screen.findByText('chat home')).toBeInTheDocument();
  });

  it('explains a rejected key (401) and stays on the form', async () => {
    const signIn = vi
      .fn()
      .mockRejectedValue(
        new ApiError({ type: 'https://netcore.example/problems/unauthorized', status: 401 }, { status: 401 }),
      );
    setup(signIn);
    await userEvent.type(screen.getByLabelText('API key'), 'nope');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/not valid/i);
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows the API version from /health', async () => {
    setup(vi.fn());
    expect(await screen.findByText('API v0.8.0')).toBeInTheDocument();
  });

  it('keeps Continue disabled until a key is typed', () => {
    setup(vi.fn());
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
  });
});
