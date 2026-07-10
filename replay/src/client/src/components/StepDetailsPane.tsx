import { Fragment } from 'react';

type StepDetails = {
  id: string;
  runId: string;
  sequence: number;
  type: string;
  label: string | null;
  toolName: string | null;
  input: unknown;
  output: unknown;
  stateBefore: unknown;
  stateAfter: unknown;
  createdAt: string;
};

type StepDetailsPaneProps = {
  step: StepDetails | null;
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2) ?? String(value);
  } catch {
    return String(value);
  }
}

function getDiffRows(before: unknown, after: unknown) {
  const beforeLines = formatValue(before).split('\n');
  const afterLines = formatValue(after).split('\n');
  const maxLength = Math.max(beforeLines.length, afterLines.length);
  const rows = [];

  for (let index = 0; index < maxLength; index += 1) {
    const beforeLine = beforeLines[index] ?? '';
    const afterLine = afterLines[index] ?? '';
    rows.push({
      id: index,
      before: beforeLine,
      after: afterLine,
      changed: beforeLine !== afterLine,
      added: beforeLine === '' && afterLine !== '',
    });
  }

  return rows;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="details-section">
      <span className="details-section-title">{label}</span>
      <pre>{value || '—'}</pre>
    </div>
  );
}

function StepDetailsPane({ step }: StepDetailsPaneProps) {
  if (!step) {
    return (
      <div className="details-pane">
        <span className="details-pane-heading">Step Details</span>
        <div className="details-placeholder">
          <span className="details-placeholder-icon">◉</span>
          Select a node in the graph to inspect tool arguments and state changes.
        </div>
      </div>
    );
  }

  const diffRows = getDiffRows(step.stateBefore, step.stateAfter);

  return (
    <div className="details-pane fade-in">
      <span className="details-pane-heading">
        #{step.sequence} {step.label || step.toolName || step.type}
      </span>

      <div className="details-grid">
        <Field label="Step ID" value={step.id} />
        <Field label="Type" value={step.type} />
        {step.toolName && <Field label="Tool" value={step.toolName} />}
        <Field label="Timestamp" value={new Date(step.createdAt).toLocaleString()} />

        <section className="details-section">
          <h3 className="details-section-title">Tool Arguments</h3>
          <pre>{formatValue(step.input) || 'No input captured.'}</pre>
        </section>

        <section className="details-section">
          <h3 className="details-section-title">Output / Logs</h3>
          <pre>{formatValue(step.output) || 'No output captured.'}</pre>
        </section>

        {(step.stateBefore || step.stateAfter) && (
          <section className="details-section">
            <h3 className="details-section-title">Before / After Diff</h3>
            <div className="diff-grid">
              <div className="diff-header">Before</div>
              <div className="diff-header">After</div>
              {diffRows.map((row) => (
                <Fragment key={row.id}>
                  <pre
                    className={
                      row.changed
                        ? row.added
                          ? 'diff-line diff-line-added'
                          : 'diff-line diff-line-changed'
                        : 'diff-line'
                    }
                  >
                    {row.before || ' '}
                  </pre>
                  <pre
                    className={
                      row.changed
                        ? row.added
                          ? 'diff-line diff-line-added'
                          : 'diff-line diff-line-changed'
                        : 'diff-line'
                    }
                  >
                    {row.after || ' '}
                  </pre>
                </Fragment>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

export default StepDetailsPane;
