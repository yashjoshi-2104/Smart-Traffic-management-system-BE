import { useWebSocket } from "../../hooks/useWebSocket";
import { useTrafficStore } from "../../store/TrafficStore";
import PerformanceBadge from "../PerformanceBadge/PerformanceBadge";

export default function TopBar() {
  const { connectionStatus, isLive, isRunning, syncDiff } = useWebSocket();
  const { mode, baseline, rl } = useTrafficStore();

  const connColor =
    connectionStatus === "connected" ? "#00e676" :
    connectionStatus === "connecting" ? "#ffaa00" : "#ff3255";

  const connLabel =
    connectionStatus === "connected" ? "CONNECTED" :
    connectionStatus === "connecting" ? "CONNECTING…" : "OFFLINE";

  return (
    <header className="top-bar">
      {/* Brand */}
      <div className="tb-brand">
        <span className="tb-icon">◈</span>
        <span className="tb-name">
          VEIG<span className="tb-accent">_1</span>
        </span>
        <span className="tb-sub">Smart Signal Management System</span>
      </div>

      {/* Center pills */}
      <div className="tb-pills">
        <Pill
          label="STATUS"
          value={isRunning ? "RUNNING" : "IDLE"}
          color={isRunning ? "#00e676" : "#3a3f4d"}
        />
        <Pill label="MODE" value={mode.toUpperCase()} color="#ffaa00" />
        <Pill
          label="BASE STEP"
          value={baseline?.step?.toLocaleString() ?? "—"}
        />
        <Pill label="RL STEP" value={rl?.step?.toLocaleString() ?? "—"} />
        <Pill
          label="SYNC"
          value={`${(syncDiff ?? 0).toFixed(3)}s`}
          color={syncDiff < 0.1 ? "#00e676" : "#ffaa00"}
        />
        {isRunning && <PerformanceBadge />}
        {/* Performance Badge */}
        {isRunning && <PerformanceBadge />}
      </div>

      {/* Connection */}
      <div className="tb-conn">
        <span
          className="tb-conn-dot"
          style={{
            background: connColor,
            boxShadow: isLive ? `0 0 8px ${connColor}` : "none",
          }}
        />
        <span className="tb-conn-label" style={{ color: connColor }}>
          {connLabel}
        </span>
        <span className="tb-ws-url">ws://localhost:8000/ws</span>
      </div>

      <style>{`
        .top-bar {
          height: 46px;
          background: #0e1015;
          border-bottom: 1px solid #1e2128;
          display: flex; align-items: center;
          padding: 0 0.85rem; gap: 1rem;
          flex-shrink: 0; overflow: hidden;
        }
        .tb-brand { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
        .tb-icon { font-size: 1.1rem; color: #ffaa00; line-height: 1; }
        .tb-name {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.82rem; font-weight: 800;
          letter-spacing: 0.14em; color: #d0d5e0;
        }
        .tb-accent { color: #ffaa00; }
        .tb-sub {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.52rem; color: #2e3240;
          letter-spacing: 0.07em;
          display: none;
        }
        @media (min-width: 1100px) { .tb-sub { display: inline; } }

        .tb-pills {
          display: flex; gap: 0.35rem; flex: 1;
          align-items: center; flex-wrap: wrap;
        }

        .tb-conn {
          display: flex; align-items: center; gap: 0.45rem;
          flex-shrink: 0; margin-left: auto;
        }
        .tb-conn-dot {
          width: 7px; height: 7px; border-radius: 50%;
          animation: blink 2s ease-in-out infinite;
          flex-shrink: 0;
        }
        .tb-conn-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.62rem; font-weight: 800;
          letter-spacing: 0.1em;
        }
        .tb-ws-url {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.52rem; color: #2e3240;
          display: none;
        }
        @media (min-width: 1200px) { .tb-ws-url { display: inline; } }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.45} }
      `}</style>
    </header>
  );
}

function Pill({
  label,
  value,
  color = "#7a8090",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="tb-pill">
      <span className="tb-pill-label">{label}</span>
      <span className="tb-pill-value" style={{ color }}>
        {value}
      </span>
      <style>{`
        .tb-pill {
          display: flex; align-items: center; gap: 0.3rem;
          background: #12141a; border: 1px solid #1e2128;
          padding: 0.15rem 0.45rem;
          flex-shrink: 0;
        }
        .tb-pill-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.48rem; font-weight: 700;
          letter-spacing: 0.1em; color: #3a3f4d;
        }
        .tb-pill-value {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.62rem; font-weight: 800;
        }
      `}</style>
    </div>
  );
}