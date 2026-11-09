// Run statuses from the API (RunStatus) -> label + tone.
export const RUN_STATUS = {
  running: { label: 'Running', tone: 'info' },
  completed: { label: 'Completed', tone: 'ok' },
  client_disconnected: { label: 'Disconnected', tone: 'warn' },
  timeout: { label: 'Timeout', tone: 'bad' },
  failed: { label: 'Failed', tone: 'bad' },
};

// agent_status values (the outcome inside a completed run).
export const AGENT_STATUS = {
  answered: { label: 'Answered', tone: 'ok' },
  cache_hit: { label: 'Cache hit', tone: 'ok' },
  low_confidence: { label: 'Low confidence', tone: 'warn' },
  no_info: { label: 'No info', tone: 'warn' },
  blocked: { label: 'Blocked', tone: 'bad' },
  refused: { label: 'Refused', tone: 'bad' },
  timeout: { label: 'Timeout', tone: 'bad' },
  error: { label: 'Error', tone: 'bad' },
};

export const statusTone = (status) => RUN_STATUS[status]?.tone || 'mute';
