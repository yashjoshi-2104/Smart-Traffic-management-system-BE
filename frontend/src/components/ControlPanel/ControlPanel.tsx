// components/ControlPanel/ControlPanel.tsx
import { useState } from "react";
import { useTrafficStore } from "../../store/TrafficStore";
import { startSimulation, stopSimulation, getTrafficLights } from "../../services/apiClient";
import SpeedControl from "./SpeedControl";

const T = {
  red:       "#dc2626",
  redBg:     "rgba(220,38,38,0.08)",
  amber:     "#f59e0b",
  amberBg:   "rgba(245,158,11,0.08)",
  green:     "#16a34a",
  greenBg:   "rgba(22,163,74,0.08)",
  greenGlow: "rgba(22,163,74,0.3)",
  blue:      "#3b82f6",
  blueBg:    "rgba(59,130,246,0.08)",
  blueGlow:  "rgba(59,130,246,0.3)",
};

export default function ControlPanel() {
  const { isRunning, setIsRunning, resetHistory, setTrafficLights, connectionStatus } =
    useTrafficStore();
  const [loading, setLoading] = useState<"start" | "stop" | null>(null);
  const [error, setError]     = useState<string | null>(null);

  const connOk = connectionStatus === "connected";

  const handleStart = async () => {
    setLoading("start");
    setError(null);
    try {
      await startSimulation();
      const tls = await getTrafficLights();
      setTrafficLights(tls);
      setIsRunning(true);
    } catch (e) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? (e instanceof Error ? e.message : "Failed to start simulation"));
    } finally {
      setLoading(null);
    }
  };

  const handleStop = async () => {
    setLoading("stop");
    setError(null);
    try {
      await stopSimulation();
      setIsRunning(false);
      resetHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop simulation");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="cp">

      {/* ── Connection bar ── */}
      <div className={`cp-conn ${connectionStatus}`}>
        <div className="cp-conn-dot" />
        <span className="cp-conn-label">
          {connectionStatus === "connected"    && "CONNECTED"}
          {connectionStatus === "connecting"   && "CONNECTING…"}
          {connectionStatus === "disconnected" && "OFFLINE"}
        </span>
        <span className="cp-conn-ws">ws://localhost:8000</span>
      </div>

      {/* ── Simulation section ── */}
      <div className="cp-section">
        <span className="cp-section-label">SIMULATION</span>
        <div className="cp-btns">
          <button
            className="cp-btn cp-start"
            onClick={handleStart}
            disabled={isRunning || loading !== null || !connOk}
          >
            <span>▶</span>
            {loading === "start" ? "STARTING…" : "START"}
          </button>
          <button
            className="cp-btn cp-stop"
            onClick={handleStop}
            disabled={!isRunning || loading !== null}
          >
            <span>■</span>
            {loading === "stop" ? "STOPPING…" : "STOP"}
          </button>
        </div>

        <div className={`cp-status ${isRunning ? "running" : "idle"}`}>
          <div className="cp-status-dot" />
          <span className="cp-status-label">
            {isRunning ? "SIMULATION ACTIVE" : "SIMULATION IDLE"}
          </span>
        </div>
      </div>

      <div className="cp-divider" />

      {/* ── Algorithm status (replaces mode selector) ── */}
      <div className="cp-section">
        <span className="cp-section-label">ACTIVE ALGORITHMS</span>

        {/* Baseline — always fixed time */}
        <div className="cp-algo cp-algo-baseline">
          <div className="cp-algo-dot cp-algo-dot-fixed" />
          <div className="cp-algo-info">
            <span className="cp-algo-name">BASELINE</span>
            <span className="cp-algo-desc">Fixed-time · 30s / 30s cycle</span>
          </div>
          <span className="cp-algo-tag cp-algo-tag-fixed">FIXED</span>
        </div>

        {/* RL sim — always DDQN */}
        <div className={`cp-algo cp-algo-rl ${isRunning ? "active" : ""}`}>
          <div className={`cp-algo-dot cp-algo-dot-rl ${isRunning ? "pulse" : ""}`} />
          <div className="cp-algo-info">
            <span className="cp-algo-name">RL AGENT</span>
            <span className="cp-algo-desc">D-DQN · 25-value state</span>
          </div>
          <span className="cp-algo-tag cp-algo-tag-rl">DDQN</span>
        </div>

        <p className="cp-algo-note">
          Both simulations run simultaneously on identical traffic scenarios for unbiased real-time comparison.
        </p>
      </div>

      <div className="cp-divider" />

      {/* ── Speed ── */}
      <div className="cp-section">
        <SpeedControl disabled={!isRunning} onError={setError} />
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="cp-error" onClick={() => setError(null)}>
          <span style={{ color: T.red, fontSize: "0.7rem" }}>⚠</span>
          <span className="cp-error-msg">{error}</span>
          <span style={{ color: `${T.red}66`, fontSize: "0.6rem" }}>✕</span>
        </div>
      )}

      <style>{`
        .cp { display:flex; flex-direction:column; flex:1; background:#f2f1ec; }

        /* Connection */
        .cp-conn { display:flex; align-items:center; gap:7px; padding:8px 12px; border-bottom:1px solid #e2ddd5; background:#fff; }
        .cp-conn-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; animation:signal-pulse 2s ease-in-out infinite; }
        .cp-conn.connected    .cp-conn-dot { background:${T.green}; box-shadow:0 0 6px ${T.greenGlow}; }
        .cp-conn.connecting   .cp-conn-dot { background:${T.amber}; box-shadow:0 0 6px rgba(245,158,11,0.4); animation:amber-pulse 1.5s ease-in-out infinite; }
        .cp-conn.disconnected .cp-conn-dot { background:${T.red}; animation:red-pulse 1s ease-in-out infinite; }
        .cp-conn-label { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; letter-spacing:0.1em; flex:1; }
        .cp-conn.connected    .cp-conn-label { color:${T.green}; }
        .cp-conn.connecting   .cp-conn-label { color:${T.amber}; }
        .cp-conn.disconnected .cp-conn-label { color:${T.red}; }
        .cp-conn-ws { font-family:'JetBrains Mono',monospace; font-size:7px; color:#a1a1aa; }

        /* Sections */
        .cp-section { padding:12px; display:flex; flex-direction:column; gap:8px; }
        .cp-section-label { font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700; letter-spacing:0.16em; color:#71717a; }
        .cp-divider { height:1px; background:#e2ddd5; flex-shrink:0; }

        /* Buttons */
        .cp-btns { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
        .cp-btn { display:flex; align-items:center; justify-content:center; gap:5px; padding:10px 6px; font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:800; letter-spacing:0.06em; border:1px solid; border-radius:6px; cursor:pointer; transition:all 0.15s; }
        .cp-btn:disabled { opacity:0.3; cursor:not-allowed; }
        .cp-start { background:${T.greenBg}; border-color:${T.green}; color:${T.green}; }
        .cp-start:hover:not(:disabled) { background:rgba(22,163,74,0.15); box-shadow:0 0 12px ${T.greenGlow}; }
        .cp-stop  { background:${T.redBg};   border-color:${T.red};   color:${T.red}; }
        .cp-stop:hover:not(:disabled) { background:rgba(220,38,38,0.15); box-shadow:0 0 12px rgba(220,38,38,0.3); }

        /* Status */
        .cp-status { display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:6px; border:1px solid; }
        .cp-status.idle    { background:#fff; border-color:#e2ddd5; }
        .cp-status.running { background:${T.greenBg}; border-color:${T.green}33; }
        .cp-status-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
        .cp-status.idle    .cp-status-dot { background:#e2ddd5; }
        .cp-status.running .cp-status-dot { background:${T.green}; box-shadow:0 0 8px ${T.greenGlow}; animation:signal-pulse 1.5s ease-in-out infinite; }
        .cp-status-label { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; letter-spacing:0.06em; }
        .cp-status.idle    .cp-status-label { color:#a1a1aa; }
        .cp-status.running .cp-status-label { color:${T.green}; }

        /* Algorithm status cards */
        .cp-algo { display:flex; align-items:center; gap:10px; padding:9px 12px; border-radius:6px; border:1px solid #e2ddd5; background:#fff; }
        .cp-algo-rl.active { background:${T.blueBg}; border-color:${T.blue}33; }
        .cp-algo-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
        .cp-algo-dot-fixed { background:${T.amber}; }
        .cp-algo-dot-rl    { background:#d1d5db; }
        .cp-algo-dot-rl.pulse { background:${T.blue}; box-shadow:0 0 8px ${T.blueGlow}; animation:signal-pulse 2s ease-in-out infinite; }
        .cp-algo-info { display:flex; flex-direction:column; gap:2px; flex:1; }
        .cp-algo-name { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:800; letter-spacing:0.08em; color:#18181b; }
        .cp-algo-desc { font-family:'JetBrains Mono',monospace; font-size:8px; color:#a1a1aa; }
        .cp-algo-tag { font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700; letter-spacing:0.1em; padding:2px 6px; border:1px solid; border-radius:2px; }
        .cp-algo-tag-fixed { color:${T.amber}; border-color:${T.amber}44; background:${T.amberBg}; }
        .cp-algo-tag-rl    { color:${T.blue};  border-color:${T.blue}44;  background:${T.blueBg};  }
        .cp-algo-note { font-family:'JetBrains Mono',monospace; font-size:8px; color:#a1a1aa; line-height:1.5; margin:0; }

        /* Error */
        .cp-error { margin:0 12px 12px; display:flex; align-items:flex-start; gap:6px; padding:8px 10px; background:${T.redBg}; border:1px solid rgba(220,38,38,0.35); border-radius:6px; cursor:pointer; }
        .cp-error-msg { font-family:'JetBrains Mono',monospace; font-size:9px; color:${T.red}; flex:1; line-height:1.4; }

        @keyframes signal-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
        @keyframes amber-pulse  { 0%,100%{opacity:1} 50%{opacity:0.5} }
        @keyframes red-pulse    { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes slide-up     { from{opacity:0;transform:translateY(4px)} }
      `}</style>
    </div>
  );
}