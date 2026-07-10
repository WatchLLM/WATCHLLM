type PlaybackControlsProps = {
  currentIndex: number;
  totalSteps: number;
  isPlaying: boolean;
  onPlay: () => void;
  onPause: () => void;
  onStepBack: () => void;
  onStepForward: () => void;
};

function PlaybackControls({
  currentIndex,
  totalSteps,
  isPlaying,
  onPlay,
  onPause,
  onStepBack,
  onStepForward,
}: PlaybackControlsProps) {
  const hasSteps = totalSteps > 0;
  const progressPct = totalSteps > 1
    ? Math.round((currentIndex / (totalSteps - 1)) * 100)
    : 0;

  return (
    <div className="playback-controls">
      <div className="playback-info">
        <span className="playback-label">Playback</span>
        <span className="playback-status">
          {hasSteps ? `Step ${currentIndex + 1} / ${totalSteps}` : 'No steps'}
        </span>
      </div>

      <div className="playback-progress" aria-hidden="true">
        <div
          className="playback-progress-fill"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <div className="playback-buttons" role="group" aria-label="Playback controls">
        <button
          id="pb-step-back"
          type="button"
          className="pb-btn"
          onClick={onStepBack}
          disabled={!hasSteps || currentIndex <= 0}
          aria-label="Step back"
          title="Step back"
        >
          ‹‹
        </button>

        {isPlaying ? (
          <button
            id="pb-pause"
            type="button"
            className="pb-btn primary"
            onClick={onPause}
            aria-label="Pause"
            title="Pause"
          >
            ⏸ Pause
          </button>
        ) : (
          <button
            id="pb-play"
            type="button"
            className="pb-btn primary"
            onClick={onPlay}
            disabled={!hasSteps}
            aria-label="Play"
            title="Play"
          >
            ▶ Play
          </button>
        )}

        <button
          id="pb-step-forward"
          type="button"
          className="pb-btn"
          onClick={onStepForward}
          disabled={!hasSteps || currentIndex >= totalSteps - 1}
          aria-label="Step forward"
          title="Step forward"
        >
          ››
        </button>
      </div>
    </div>
  );
}

export default PlaybackControls;
