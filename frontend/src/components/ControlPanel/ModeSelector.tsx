// components/ControlPanel/ModeSelector.tsx
import { useTrafficStore } from "../../store/TrafficStore";
import { setControlMode } from "../../services/apiClient";
import type { ControlMode } from "../../types";

// Traffic signal colours for mode dots
// Fixed Time → amber  (caution — not optimal, predetermined)
// RL Agent   → green  (go — adaptive, intelligent)
const MODES: {
  value: ControlMode;
  label: string;
  desc: string;
  sigColor: string;
  sigBg: string;
  sigGlow: string;
}[] = [
  {
    value:    "fixed",
    label:    "Fixed Time",
    desc:     "Predetermined 30s · 30s cycle",
    sigColor: "#f59e0b",
    sigBg:    "rgba(245,158,11,0.08)",
    sigGlow:  "rgba(245,158,11,0.35)",
  },
  {
    value:    "rl",
    label:    "RL Agent",
    desc:     "DDQN adaptive signal control",
    sigColor: "#16a34a",
    sigBg:    "rgba(22,163,74,0.08)",
    sigGlow:  "rgba(22,163,74,0.3)",
  },
];

interface Props {
  disabled?: boolean;
  onError?: (msg: string) => void;
}

export default function ModeSelector({ disabled, onError }: Props) {
  const { mode, setMode } = useTrafficStore();

  const handleSelect = async (m: ControlMode) => {
    if (m === mode || disabled) return;
    try {
      await setControlMode(m);
      setMode(m);
    } catch {
      onError?.(`Failed to switch to ${m} mode`);
    }
  };

  return (
    <div className="ms">
      <span className="ms-label">CONTROL MODE</span>
      <div className="ms-options">
        {MODES.map(({ value, label, desc, sigColor, sigBg, sigGlow }) => {
          const active = mode === value;
          return (
            <button
              key={value}
              className={`ms-option ${active ? "active" : ""}`}
              style={active ? {
                background: sigBg,
                borderColor: `${sigColor}55`,
              } : {}}
              onClick={() => handleSelect(value)}
              disabled={disabled}
            >
              <div className="ms-top">
                {/* Traffic signal dot — amber for fixed, green for RL */}
                <div
                  className="ms-dot"
                  style={{
                    background: active ? sigColor : `${sigColor}35`,
                    boxShadow:  active ? `0 0 8px ${sigGlow}` : "none",
                    animation:  active
                      ? sigColor === "#f59e0b"
                        ? "amber-pulse 2s ease-in-out infinite"
                        : "signal-pulse 2s ease-in-out infinite"
                      : "none",
                  }}
                />
                <span
                  className="ms-name"
                  style={{ color: active ? sigColor : "#71717a" }}
                >
                  {label}
                </span>
                {active && (
                  <span
                    className="ms-badge"
                    style={{ color: sigColor, borderColor: `${sigColor}44` }}
                  >
                    ACTIVE
                  </span>
                )}
              </div>
              <span className="ms-desc">{desc}</span>
            </button>
          );
        })}
      </div>

      <style>{`
        .ms { display:flex; flex-direction:column; gap:6px; }
        .ms-label { font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700; letter-spacing:0.16em; color:#71717a; }
        .ms-options { display:flex; flex-direction:column; gap:5px; }
        .ms-option {
          background:#fff; border:1px solid #e2ddd5;
          padding:10px 12px; cursor:pointer;
          display:flex; flex-direction:column; gap:3px;
          text-align:left; transition:all 0.2s; border-radius:6px;
        }
        .ms-option:hover:not(:disabled):not(.active) { border-color:#c8c3ba; background:#fafaf7; }
        .ms-option:disabled { opacity:0.35; cursor:not-allowed; }
        .ms-top { display:flex; align-items:center; gap:7px; }
        .ms-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; transition:all 0.3s; }
        .ms-name { font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; letter-spacing:0.06em; flex:1; }
        .ms-badge { font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700; letter-spacing:0.1em; padding:2px 6px; border:1px solid; border-radius:2px; }
        .ms-desc { font-family:'JetBrains Mono',monospace; font-size:9px; color:#a1a1aa; padding-left:15px; }
        .ms-option.active .ms-desc { color:#71717a; }
      `}</style>
    </div>
  );
}