// components/ControlPanel/SpeedControl.tsx
import { useState } from "react";
import { simulationAPI } from "../../services/apiClient";

const SPEED_PRESETS = [
  { label: "0.01×", value: 0.01 },
  { label: "0.25×", value: 0.25 },
  { label: "0.5×",  value: 0.5  },
  { label: "1×",    value: 1    },
  { label: "2×",    value: 2    },
];

interface Props {
  disabled?: boolean;
  onError?: (msg: string) => void;
}

export default function SpeedControl({ disabled, onError }: Props) {
  const [speed,   setSpeed]   = useState(1);
  const [loading, setLoading] = useState(false);

  const handleSet = async (val: number) => {
    if (disabled || loading) return;
    setLoading(true);
    try {
      await simulationAPI.setSpeed(val);
      setSpeed(val);
    } catch {
      onError?.(`Failed to set speed to ${val}×`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sc-wrap">
      <span className="sc-label">SIM SPEED</span>

      <div className="sc-presets">
        {SPEED_PRESETS.map(p => (
          <button
            key={p.value}
            className={`sc-btn ${speed === p.value ? "sc-active" : ""}`}
            onClick={() => handleSet(p.value)}
            disabled={disabled || loading}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="sc-current">
        <span className="sc-cur-label">CURRENT</span>
        <span className="sc-cur-val">{speed}×</span>
      </div>

      <style>{`
        .sc-wrap { display:flex; flex-direction:column; gap:8px; }

        .sc-label {
          font-family:'JetBrains Mono',monospace;
          font-size:8px; font-weight:700;
          letter-spacing:0.16em; color:#71717a;
        }

        /* 5 buttons in a row */
        .sc-presets {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 4px;
        }

        .sc-btn {
          background: #fff;
          border: 1px solid #e2ddd5;
          color: #71717a;
          padding: 7px 2px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.15s;
          border-radius: 4px;
          letter-spacing: 0.02em;
        }
        .sc-btn:hover:not(:disabled):not(.sc-active) {
          border-color: #c8c3ba;
          color: #3f3f46;
          background: #fafaf7;
        }
        /* Active = amber — traffic signal easter egg (caution speed) */
        .sc-btn.sc-active {
          background: rgba(245,158,11,0.1);
          border-color: #f59e0b;
          color: #f59e0b;
          font-weight: 800;
        }
        .sc-btn:disabled { opacity:0.35; cursor:not-allowed; }

        /* Current speed readout */
        .sc-current {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 10px;
          background: #fff;
          border: 1px solid #e2ddd5;
          border-radius: 4px;
        }
        .sc-cur-label {
          font-family:'JetBrains Mono',monospace;
          font-size:8px; font-weight:700;
          letter-spacing:0.1em; color:#a1a1aa;
        }
        .sc-cur-val {
          font-family:'JetBrains Mono',monospace;
          font-size:12px; font-weight:800;
          color: #f59e0b;
        }
      `}</style>
    </div>
  );
}