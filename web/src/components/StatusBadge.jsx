import { AGENT_STATUS, RUN_STATUS } from '../lib/status';
import { Pill } from './ui';

export function StatusBadge({ status }) {
  const s = RUN_STATUS[status] || { label: status || 'Unknown', tone: 'mute' };
  return (
    <Pill tone={s.tone} dot pulse={status === 'running'}>
      {s.label}
    </Pill>
  );
}

export function OutcomeBadge({ agentStatus }) {
  if (!agentStatus) return <span className="text-ink-3">–</span>;
  const s = AGENT_STATUS[agentStatus] || { label: agentStatus, tone: 'mute' };
  return <Pill tone={s.tone}>{s.label}</Pill>;
}
