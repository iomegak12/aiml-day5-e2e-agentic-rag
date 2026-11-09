import { useEffect, useRef, useState } from 'react';
import { ErrorView } from '../../components/errors/ErrorCards';
import { RateLimitBanner } from '../../components/errors/RateLimitBanner';
import { Icon, Spinner } from '../../components/ui';
import { QUESTION_MAX, QUESTION_MIN, toAskBody } from './askBody';
import { ModePill } from './ModePill';
import { OptionsPopover } from './OptionsPopover';

/**
 * Question box with mode pill, options popover and send button.
 * Enter sends, Shift+Enter adds a line. Shows 429 / 422 / other API errors from `error`.
 */
export function Composer({
  initial = {},
  onSubmit,
  pending = false,
  error = null,
  onClearError,
  disabled = false,
  disabledHint,
  placeholder = 'Ask about NetCore SD-WAN, Meet or Calling…',
  autoFocus = false,
  compact = false,
}) {
  const [question, setQuestion] = useState(initial.question || '');
  const [mode, setMode] = useState(initial.mode || 'plan');
  const [options, setOptions] = useState({
    timeout: initial.timeout || null,
    includeTrace: true,
    bypassCache: false,
  });
  const ref = useRef(null);

  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);

  const rateLimited = error?.status === 429;
  const fieldErrors = error?.status === 422 ? error.fieldErrors : {};
  const text = question.trim();
  const tooShort = text.length > 0 && text.length < QUESTION_MIN;
  const canSend =
    !disabled && !pending && !rateLimited && text.length >= QUESTION_MIN && text.length <= QUESTION_MAX;

  function send() {
    if (canSend) onSubmit(toAskBody({ question, mode, ...options }));
  }

  return (
    <div className="space-y-2">
      {rateLimited && <RateLimitBanner retryAfter={error.retryAfter} onDone={onClearError} />}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className={`rounded-2xl border border-line bg-card shadow-sm transition focus-within:border-line-strong ${
          rateLimited || disabled ? 'opacity-70' : ''
        }`}
      >
        <label htmlFor="composer" className="sr-only">
          Your question
        </label>
        <textarea
          id="composer"
          ref={ref}
          rows={compact ? 2 : 4}
          maxLength={QUESTION_MAX}
          value={question}
          disabled={disabled || rateLimited}
          placeholder={disabled && disabledHint ? disabledHint : placeholder}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              send();
            }
          }}
          aria-invalid={Boolean(fieldErrors.question) || tooShort}
          className="block w-full resize-none bg-transparent px-4 pt-4 text-[15px] outline-none placeholder:text-ink-3"
        />
        <div className="flex items-center justify-between gap-2 px-3 pt-1 pb-3">
          <div className="flex items-center gap-2">
            <ModePill value={mode} onChange={setMode} disabled={disabled} />
            <OptionsPopover
              value={options}
              onChange={setOptions}
              disabled={disabled}
              error={fieldErrors.timeout_seconds}
            />
            {(tooShort || fieldErrors.question) && (
              <span className="text-xs text-bad">
                {fieldErrors.question || `At least ${QUESTION_MIN} characters`}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {text.length > QUESTION_MAX * 0.9 && (
              <span className="font-mono text-xs text-ink-3">
                {text.length}/{QUESTION_MAX}
              </span>
            )}
            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send question"
              className="inline-flex size-9 items-center justify-center rounded-full bg-primary text-on-primary transition hover:opacity-90 disabled:bg-line disabled:text-ink-3"
            >
              {pending ? (
                <Spinner className="border-on-primary/40 border-t-on-primary" />
              ) : (
                <Icon name="arrow_upward" />
              )}
            </button>
          </div>
        </div>
      </form>
      {error && !rateLimited && error.status !== 422 && error.status !== 401 && (
        <ErrorView error={error} question={question} mode={mode} />
      )}
    </div>
  );
}
