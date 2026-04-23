import { useState } from "react";
import api from "../../services/apiClient";

const DURATION_PRESETS = [10, 20, 30, 45, 60];

interface Props {
  tlId: string;
  disabled?: boolean;
  onError?: (msg: string) => void;
}

export default function TimingControls({ tlId, disabled, onError }: Props) {
  const [greenDuration,  setGreenDuration]  = useState(30);
  const [yellowDuration, setYellowDuration] = useState(5);
  const [loading, setLoading] = useState(false);
  const [applied, setApplied] = useState(false);

  const handleApply = async () => {
    if (disabled || loading) return;
    setLoading(true);
    setApplied(false);
    try {
      await api.post("/api/control/set_timing", {
        tl_id:           tlId,
        green_duration:  greenDuration,
        yellow_duration: yellowDuration,
      });
      setApplied(true);
      setTimeout(() => setApplied(false), 2000);
    } catch {
      onError?.("Failed to update signal timing");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="timing-controls">
      <span className="tc-label">PHASE TIMING</span>

      <div className="tc-row">
        <div className="tc-field">
          <span className="tc-field-label">GREEN</span>
          <div className="tc-input-wrap">
            <input
              type="number"
              className="tc-input"
              value={greenDuration}
              min={5} max={120} step={5}
              disabled={disabled}
              onChange={(e) => setGreenDuration(Number(e.target.value))}
            />
            <span className="tc-unit">s</span>
          </div>
        </div>
        <div className="tc-field">
          <span className="tc-field-label">YELLOW</span>
          <div className="tc-input-wrap">
            <input
              type="number"
              className="tc-input"
              value={yellowDuration}
              min={3} max={15} step={1}
              disabled={disabled}
              onChange={(e) => setYellowDuration(Number(e.target.value))}
            />
            <span className="tc-unit">s</span>
          </div>
        </div>
      </div>

      <div className="tc-presets">
        {DURATION_PRESETS.map((d) => (
          <button
            key={d}
            className={`tc-preset ${greenDuration === d ? "active" : ""}`}
            onClick={() => setGreenDuration(d)}
            disabled={disabled}
          >
            {d}s
          </button>
        ))}
      </div>

      <button
        className={`tc-apply ${applied ? "applied" : ""}`}
        onClick={handleApply}
        disabled={disabled || loading}
      >
        {loading ? "APPLYING…" : applied ? "✓ APPLIED" : "APPLY TIMING"}
      </button>

      <style>{`
        .timing-controls { display: flex; flex-direction: column; gap: 0.5rem; }
        .tc-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; font-weight: 700;
          letter-spacing: 0.14em; color: #4a5060;
        }
        .tc-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; }
        .tc-field { display: flex; flex-direction: column; gap: 0.25rem; }
        .tc-field-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.52rem; color: #3a3f4d;
          font-weight: 700; letter-spacing: 0.1em;
        }
        .tc-input-wrap {
          display: flex; align-items: center;
          background: #0e1015; border: 1px solid #1e2128;
        }
        .tc-input {
          background: transparent; border: none; outline: none;
          color: #c8cdd8; padding: 0.35rem 0.5rem;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.75rem; font-weight: 700; width: 100%;
          -moz-appearance: textfield;
        }
        .tc-input::-webkit-inner-spin-button,
        .tc-input::-webkit-outer-spin-button { -webkit-appearance: none; }
        .tc-input:disabled { opacity: 0.4; }
        .tc-unit {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.6rem; color: #3a3f4d;
          padding: 0 0.4rem 0 0; white-space: nowrap;
        }
        .tc-presets { display: flex; gap: 0.25rem; flex-wrap: wrap; }
        .tc-preset {
          background: #12141a; border: 1px solid #1e2128;
          color: #4a5060; padding: 0.25rem 0.45rem;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.6rem; font-weight: 700;
          cursor: pointer; transition: all 0.15s;
        }
        .tc-preset.active {
          border-color: #00e676; color: #00e676;
          background: rgba(0,230,118,0.08);
        }
        .tc-preset:hover:not(:disabled):not(.active) {
          border-color: #2e3240; color: #7a8090;
        }
        .tc-preset:disabled { opacity: 0.35; cursor: not-allowed; }
        .tc-apply {
          background: #12141a; border: 1px solid #2e3240;
          color: #7a8090; padding: 0.45rem;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.65rem; font-weight: 800;
          letter-spacing: 0.12em; cursor: pointer; transition: all 0.15s;
        }
        .tc-apply:hover:not(:disabled) {
          border-color: #ffaa00; color: #ffaa00;
          background: rgba(255,170,0,0.08);
        }
        .tc-apply.applied {
          border-color: #00e676; color: #00e676;
          background: rgba(0,230,118,0.08);
        }
        .tc-apply:disabled { opacity: 0.35; cursor: not-allowed; }
      `}</style>
    </div>
  );
}