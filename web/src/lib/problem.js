// RFC 9457 problem helpers. The API's problem types look like https://netcore.example/problems/<slug>.

export const slugOf = (type = '') => type.split('/').filter(Boolean).pop() || 'about:blank';

export const PROBLEM_COPY = {
  unauthorized: { title: 'Your key is not valid', hint: 'Sign in again with a valid X-API-Key.' },
  'rate-limited': {
    title: 'You are sending requests too fast',
    hint: 'Wait for the countdown, then try again.',
  },
  'validation-error': { title: 'Please check your input', hint: 'Some fields are out of range.' },
  'not-found': { title: 'Request not found', hint: 'It does not exist, or it belongs to another user.' },
  'agent-timeout': {
    title: 'This is taking longer than expected',
    hint: 'The run may still finish in the background.',
  },
  'agent-failed': { title: 'The assistant could not complete the request', hint: 'Try again in a moment.' },
  'not-ready': { title: 'Assistant temporarily unavailable', hint: 'A backing service is not ready.' },
  'internal-error': {
    title: 'Something went wrong',
    hint: 'Try again; quote the request id if it persists.',
  },
  network: { title: 'Cannot reach the API', hint: 'Check that the API (and Nginx) are running.' },
};

export const copyFor = (slug) => PROBLEM_COPY[slug] || { title: 'Unexpected error', hint: '' };
