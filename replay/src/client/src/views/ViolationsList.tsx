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
      location?: any;
    }>;
  };
}

export default function ViolationsList() {
  const [violations, setViolations] = useState<ViolationReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/violations')
      .then((res) => {
        if (!res.ok) {
          throw new Error('Failed to fetch violations');
        }
        return res.json();
      })
      .then((data) => {
        setViolations(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading">Loading violations...</div>;
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  return (
    <div className="view-container">
      <header className="view-header">
        <h1>Governance Violations</h1>
      </header>

      {violations.length === 0 ? (
        <div className="empty-state">
          <p>No violations recorded yet.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Trace/Run ID</th>
                <th>File</th>
                <th>Rule</th>
                <th>Severity</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {violations.flatMap((v) => 
                v.report.violations ? v.report.violations.map((detail, idx) => (
                  <tr key={`${v.id}-${idx}`}>
                    <td>{new Date(v.created_at).toLocaleString()}</td>
                    <td>
                      <Link to={`/runs/${v.run_id}`} className="run-link">
                        {v.run_id.substring(0, 8)}...
                      </Link>
                    </td>
                    <td><code className="inline-code">{v.report.file_path}</code></td>
                    <td><span className="badge rule-badge">{detail.rule_id}</span></td>
                    <td>
                      <span className={`badge severity-${detail.severity.toLowerCase()}`}>
                        {detail.severity}
                      </span>
                    </td>
                    <td>{detail.message}</td>
                  </tr>
                )) : []
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
