import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface ViolationReport {
  id: string;
  run_id: string;
  created_at: string;
  report: {
    decision: string;
    file_path: string;
    language: string;
    mode: string;
    timestamp: string;
    trace_id?: string;
    violations: Array<{
      rule_id: string;
      message: string;
      severity: string;
      evidence: string;
      location?: Record<string, unknown>;
    }>;
  };
}

function severityClass(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical': return 'badge severity-critical';
    case 'high':     return 'badge severity-high';
    case 'medium':   return 'badge severity-medium';
    case 'low':      return 'badge severity-low';
    default:         return 'badge severity-medium';
  }
}

export default function ViolationsList() {
  const [violations, setViolations] = useState<ViolationReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/violations')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch violations');
        return res.json();
      })
      .then((data) => {
        setViolations(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="state-message">
        <div className="spinner" />
        Loading violations…
      </div>
    );
  }

  if (error) {
    return <div className="error-message">⚠ {error}</div>;
  }

  const totalRows = violations.reduce(
    (acc, v) => acc + (v.report.violations?.length ?? 0),
    0
  );

  return (
    <div className="view-container fade-up">
      <header className="view-header">
        <h1>Governance Violations</h1>
        <p>
          {totalRows > 0
            ? `${totalRows} violation${totalRows !== 1 ? 's' : ''} across ${violations.length} run${violations.length !== 1 ? 's' : ''}`
            : 'All clear — no violations recorded yet.'}
        </p>
      </header>

      {violations.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-icon">✓</span>
          No violations found. The kernel has not blocked any saves yet.
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Trace / Run</th>
                <th>File</th>
                <th>Rule</th>
                <th>Severity</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {violations.flatMap((v) =>
                v.report.violations
                  ? v.report.violations.map((detail, idx) => (
                      <tr key={`${v.id}-${idx}`}>
                        <td className="run-meta">
                          {new Date(v.created_at).toLocaleString()}
                        </td>
                        <td>
                          <Link to={`/runs/${v.run_id}`} className="run-link">
                            {v.run_id.substring(0, 8)}…
                          </Link>
                        </td>
                        <td>
                          <code className="inline-code">{v.report.file_path}</code>
                        </td>
                        <td>
                          <span className="badge rule-badge">{detail.rule_id}</span>
                        </td>
                        <td>
                          <span className={severityClass(detail.severity)}>
                            {detail.severity}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                          {detail.message}
                        </td>
                      </tr>
                    ))
                  : []
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
