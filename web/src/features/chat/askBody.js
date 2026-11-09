// AskRequest limits (api/app/schemas/agent.py). Extra fields are rejected by the API (extra=forbid).
export const QUESTION_MIN = 3;
export const QUESTION_MAX = 2000;
export const TIMEOUT_MIN = 10;
export const TIMEOUT_MAX = 300;

/** Build the AskRequest body from composer state. */
export function toAskBody({ question, mode, timeout, includeTrace = true, bypassCache = false }) {
  const body = { question: question.trim(), mode, include_trace: includeTrace, bypass_cache: bypassCache };
  if (timeout) body.timeout_seconds = timeout;
  return body;
}
