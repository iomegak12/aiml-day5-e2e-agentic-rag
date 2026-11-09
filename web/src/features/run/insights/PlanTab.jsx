import { EmptyState } from '../../../components/ui';
import { PlanSteps } from '../PlanSteps';

/** Every plan version (v1 + re-plans) with the executed outcome of each step. */
export function PlanTab({ result }) {
  const versions = result.plan?.versions || [];
  if (!versions.length) {
    return (
      <EmptyState
        icon="account_tree"
        title={result.mode === 'react' ? 'ReAct mode: no plan' : 'No plan recorded'}
      >
        {result.mode === 'react'
          ? `The agent chose its tools step by step${
              result.routes?.length ? ` (routes: ${result.routes.join(', ')})` : ''
            }. See Tool calls.`
          : 'This run finished without planning (for example a cache hit or a guardrail block).'}
      </EmptyState>
    );
  }
  return (
    <div className="space-y-3">
      {result.plan.replans > 0 && (
        <p className="text-xs text-ink-2">
          Re-planned {result.plan.replans} {result.plan.replans === 1 ? 'time' : 'times'} after steps found no
          relevant context.
        </p>
      )}
      {versions.map((v) => {
        const executed = (result.executed_plan || []).filter((s) => s.version === v.version);
        const steps = v.steps.map((s) => executed.find((e) => e.id === s.id) || s);
        return <PlanSteps key={v.version} plan={v} steps={steps} compact />;
      })}
    </div>
  );
}
