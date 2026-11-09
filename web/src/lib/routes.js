/** Where a run opens: the answer if completed, the live view if running, detail/replay otherwise. */
export function runLink(run) {
  if (run.status === 'running') return `/runs/${run.request_id}/live`;
  if (run.status === 'completed') return `/runs/${run.request_id}`;
  return `/requests/${run.request_id}`;
}
