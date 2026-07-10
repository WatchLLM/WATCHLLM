import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import RunsList from './views/RunsList';
import RunGraph from './views/RunGraph';
import ViolationsList from './views/ViolationsList';

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-eyebrow">WatchLLM</span>
          <h2 className="sidebar-title">Re<span>play</span></h2>
        </div>

        <nav>
          <ul className="sidebar-nav">
            <li>
              <NavLink
                to="/runs"
                className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
              >
                <span className="nav-icon">◈</span>
                Runs
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/violations"
                className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
              >
                <span className="nav-icon">⚡</span>
                Violations
              </NavLink>
            </li>
          </ul>
        </nav>

        <div className="sidebar-footer">
          v0.1.0 · forensics engine
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/runs" replace />} />
          <Route path="/runs" element={<RunsList />} />
          <Route path="/runs/:runId" element={<RunGraph />} />
          <Route path="/violations" element={<ViolationsList />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
