import { EmptyState } from '../../../components/ui';
import { TraceConsole } from '../TraceConsole';

export function TraceTab({ trace, traceIncluded = true }) {
  if (!trace?.length) {
    return (
      <EmptyState icon="terminal" title="No trace">
        {traceIncluded
          ? 'Nothing was traced for this run.'
          : 'Trace was not requested (include_trace=false).'}
      </EmptyState>
    );
  }
  return <TraceConsole trace={trace} maxHeight="max-h-[60vh]" />;
}
