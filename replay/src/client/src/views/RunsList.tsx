import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

type Run = {
  id: string;
  name: string | null;
  metadata: unknown;
  createdAt: string;
};

function RunsList() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchRuns() {
      try {
        const response = await fetch('/api/runs');
        if (!response.ok) {
          throw new Error(`Server responded with ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setRuns(data.runs ?? []);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch runs');
          setLoading(false);
        }
      }
    }

    fetchRuns();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="state-message">
        <div className="spinner" />
        Loading runs…
      </div>
    );
  }

  if (error) {
    return <div className="error-message">⚠ {error}</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="state-message fade-up">
        <div className="state-message-icon">◈</div>
        No runs found. Ingest a run to see it here.
      </div>
    );
  }

  return (
    <div className="fade-up">
      <h1 className="page-header">Agent Runs</h1>
      <p className="page-subtitle">Select a run to replay its execution graph.</p>
      <div className="runs-grid">
        {runs.map((run, i) => (
          <Link
            key={run.id}
            className="run-card-link"
            to={`/runs/${run.id}`}
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            <div className="run-card">
              <div className="run-card-icon">◈</div>
              <h3>{run.name ?? 'Untitled run'}</h3>
              <p className="run-meta">
                <strong>ID</strong> {run.id}
              </p>
              <p className="run-meta">
                <strong>Created</strong>{' '}
                {new Date(run.createdAt).toLocaleString()}
              </p>
              {run.metadata && (
                <>
                  <div className="run-card-divider" />
                  <div className="metadata-preview">
                    <pre>{JSON.stringify(run.metadata, null, 2)}</pre>
                  </div>
                </>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default RunsList;
