import { Tabs } from '../../../components/Tabs';
import { Dot, Icon } from '../../../components/ui';
import { JudgeTab } from './JudgeTab';
import { PlanTab } from './PlanTab';
import { SourcesTab } from './SourcesTab';
import { TimingTab } from './TimingTab';
import { ToolCallsTab } from './ToolCallsTab';
import { TraceTab } from './TraceTab';

/** "Insights & Transparency": Plan, Sources, Judge, Tool calls, Trace and Timing of an AskResponse. */
export function InsightsPanel({ result, tab, onTab, highlight }) {
  const traceIncluded = (result.trace?.length || 0) > 0 || (result.tool_calls?.length || 0) > 0;
  const tabs = [
    { id: 'plan', label: 'Plan' },
    { id: 'sources', label: 'Sources', count: result.sources?.length || 0 },
    { id: 'judge', label: 'Judge' },
    { id: 'tools', label: 'Tool calls', count: result.tool_calls?.length || 0 },
    { id: 'trace', label: 'Trace' },
    { id: 'timing', label: 'Timing' },
  ];
  return (
    <div className="space-y-3">
      <h2 className="flex items-center justify-between text-lg font-semibold">
        <span className="flex items-center gap-2">
          <Icon name="insights" /> Insights &amp; Transparency
        </span>
        <Dot tone={result.judge?.passed === false ? 'warn' : 'ok'} />
      </h2>
      <Tabs tabs={tabs} value={tab} onChange={onTab} className="flex-wrap" />
      <div role="tabpanel" className="card p-4">
        {tab === 'plan' && <PlanTab result={result} />}
        {tab === 'sources' && <SourcesTab sources={result.sources} highlight={highlight} />}
        {tab === 'judge' && <JudgeTab judge={result.judge} />}
        {tab === 'tools' && <ToolCallsTab toolCalls={result.tool_calls} traceIncluded={traceIncluded} />}
        {tab === 'trace' && <TraceTab trace={result.trace} traceIncluded={traceIncluded} />}
        {tab === 'timing' && <TimingTab result={result} />}
      </div>
    </div>
  );
}
