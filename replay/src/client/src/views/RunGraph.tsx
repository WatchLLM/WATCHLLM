import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import PlaybackControls from '../components/PlaybackControls';
import StepDetailsPane from '../components/StepDetailsPane';

type GraphRun = {
  id: string;
  name: string | null;
  metadata: unknown;
  createdAt: string;
};

type GraphStep = {
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

type GraphEdge = {
  id: number | string;
  runId: string;
  sourceStepId: string;
  targetStepId: string;
  relationship: string;
  createdAt: string;
};

type GraphResponse = {
  run: GraphRun;
  nodes: GraphStep[];
  edges: GraphEdge[];
};

/** Return a light card style for each node based on its state */
function nodeStyle(isActive: boolean, isSelected: boolean): React.CSSProperties {
  if (isActive) {
    return {
      border: '2px solid hsl(165, 100%, 55%)',
      background: 'hsl(165, 100%, 97%)',
      boxShadow: '0 0 0 4px hsla(165, 100%, 55%, 0.25)',
    };
  }
  if (isSelected) {
    return {
      border: '2px solid hsl(210, 100%, 66%)',
      background: 'hsl(210, 100%, 97%)',
      boxShadow: '0 0 0 4px hsla(210, 100%, 66%, 0.2)',
    };
  }
  return {
    border: '1px solid hsl(222, 30%, 75%)',
    background: 'hsl(0, 0%, 100%)',
  };
}

function RunGraph() {
  const { runId } = useParams<{ runId: string }>();
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchGraph() {
      try {
        const response = await fetch(`/api/runs/${runId}/graph`);
        if (!response.ok) {
          throw new Error(`Server responded with ${response.status}`);
        }
        const data: GraphResponse = await response.json();
        if (!cancelled) {
          setGraph(data);
          setCurrentStepIndex(0);
          setIsPlaying(false);
          setSelectedStepId(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch graph');
          setIsPlaying(false);
          setSelectedStepId(null);
          setLoading(false);
        }
      }
    }

    fetchGraph();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  const orderedSteps = useMemo(() => {
    if (!graph) return [];
    return [...graph.nodes].sort((a, b) => {
      if (a.sequence !== b.sequence) return a.sequence - b.sequence;
      return a.id.localeCompare(b.id);
    });
  }, [graph]);

  const activeStepId = orderedSteps[currentStepIndex]?.id ?? null;

  const selectedStep = useMemo(() => {
    if (!selectedStepId) return null;
    return orderedSteps.find((step) => step.id === selectedStepId) ?? null;
  }, [orderedSteps, selectedStepId]);

  useEffect(() => {
    if (!isPlaying || orderedSteps.length === 0) return;

    const timer = window.setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev >= orderedSteps.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        const next = prev + 1;
        if (next >= orderedSteps.length - 1) setIsPlaying(false);
        return next;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [isPlaying, orderedSteps.length]);

  function handlePlay() {
    if (orderedSteps.length === 0) return;
    if (currentStepIndex >= orderedSteps.length - 1) setCurrentStepIndex(0);
    setIsPlaying(true);
  }

  function handlePause() { setIsPlaying(false); }

  function handleStepBack() {
    setIsPlaying(false);
    setCurrentStepIndex((prev) => Math.max(prev - 1, 0));
  }

  function handleStepForward() {
    setIsPlaying(false);
    setCurrentStepIndex((prev) =>
      Math.min(prev + 1, Math.max(orderedSteps.length - 1, 0))
    );
  }

  function handleNodeClick(_event: unknown, node: Node) {
    setSelectedStepId(node.id);
  }

  const flowNodes: Node[] = useMemo(() => {
    if (!graph) return [];

    return orderedSteps.map((step, index) => {
      const isActive   = step.id === activeStepId;
      const isSelected = step.id === selectedStepId;

      return {
        id: step.id,
        position: {
          x: (index % 4) * 260,
          y: Math.floor(index / 4) * 160,
        },
        className: [
          isActive   ? 'active-flow-node'   : null,
          isSelected ? 'selected-flow-node' : null,
        ]
          .filter(Boolean)
          .join(' ') || undefined,
        style: nodeStyle(isActive, isSelected),
        data: {
          label: (
            <div className="flow-node-label">
              <strong>
                #{step.sequence} {step.label || step.toolName || step.type}
              </strong>
              <span>{step.type}</span>
              {step.toolName ? <small>{step.toolName}</small> : null}
            </div>
          ),
        },
      };
    });
  }, [orderedSteps, activeStepId, selectedStepId]);

  const flowEdges: Edge[] = useMemo(() => {
    if (!graph) return [];

    return graph.edges.map((edge) => ({
      id: String(edge.id),
      source: edge.sourceStepId,
      target: edge.targetStepId,
      label: edge.relationship,
      animated: false,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'hsl(210, 100%, 66%)',
      },
      style: { stroke: 'hsl(210, 100%, 66%)', strokeWidth: 1.5 },
    }));
  }, [graph]);

  if (loading) {
    return (
      <div className="state-message">
        <div className="spinner" />
        Loading graph…
      </div>
    );
  }

  if (error) {
    return <div className="error-message">⚠ {error}</div>;
  }

  if (!graph) {
    return <div className="error-message">Graph data not available.</div>;
  }

  if (graph.nodes.length === 0) {
    return (
      <div className="graph-page fade-up">
        <header className="graph-header">
          <Link to="/runs" className="graph-header-back">← Back to runs</Link>
          <h1>{graph.run.name ?? 'Untitled run'}</h1>
        </header>
        <div className="state-message">
          <div className="state-message-icon">◈</div>
          This run has no steps yet.
        </div>
      </div>
    );
  }

  return (
    <div className="graph-page fade-up">
      <header className="graph-header">
        <Link to="/runs" className="graph-header-back">← Back to runs</Link>
        <h1>{graph.run.name ?? 'Untitled run'}</h1>
        <p className="run-meta">
          <strong>Run ID</strong> {graph.run.id}
        </p>
      </header>

      <PlaybackControls
        currentIndex={currentStepIndex}
        totalSteps={orderedSteps.length}
        isPlaying={isPlaying}
        onPlay={handlePlay}
        onPause={handlePause}
        onStepBack={handleStepBack}
        onStepForward={handleStepForward}
      />

      <div className="graph-details-layout">
        <div className="graph-shell">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodeClick={handleNodeClick}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <MiniMap
              nodeStrokeWidth={2}
              nodeColor={(node) =>
                node.className?.includes('active-flow-node')
                  ? 'hsl(165, 100%, 55%)'
                  : node.className?.includes('selected-flow-node')
                    ? 'hsl(210, 100%, 66%)'
                    : 'hsl(222, 30%, 30%)'
              }
            />
            <Controls />
            <Background gap={20} color="hsl(222, 30%, 16%)" />
          </ReactFlow>
        </div>

        <StepDetailsPane step={selectedStep} />
      </div>
    </div>
  );
}

export default RunGraph;
