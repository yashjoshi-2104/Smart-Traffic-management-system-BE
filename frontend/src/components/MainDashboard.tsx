// components/MainDashboard.tsx
import { useWebSocket } from "../hooks/useWebSocket";
import ControlPanel from "./ControlPanel/ControlPanel";
import MetricsComparison from "./MetricsComparison/MetricsComparison";
import LiveComparison from "./LiveComparison/LiveComparison";
import { useTrafficStore } from "../store/TrafficStore";
import { useState } from "react";
import StatsCards from "./StatsCards/StatsCards";
import PerformanceBadge from "./PerformanceBadge/PerformanceBadge";
import useKeyboardShortcuts from "../hooks/useKeyboardShortcuts";
import { startSimulation, stopSimulation, getTrafficLights } from "../services/apiClient";
import SessionRecorder from "./SessionRecorder/SessionRecorder";
import { NetworkSelector } from './NetworkSelector/NetworkSelector';

// ── Traffic light signal colours ──────────────────────────────────────────────
const T = {
  red:       "#dc2626",
  redBg:     "rgba(220,38,38,0.08)",
  redGlow:   "rgba(220,38,38,0.3)",
  amber:     "#f59e0b",
  amberBg:   "rgba(245,158,11,0.08)",
  amberGlow: "rgba(245,158,11,0.3)",
  green:     "#16a34a",
  greenBg:   "rgba(22,163,74,0.08)",
  greenGlow: "rgba(22,163,74,0.3)",
};

const BRAND_LETTERS = [
  { char: "V", color: T.red,   glow: T.redGlow   },
  { char: "E", color: T.amber, glow: T.amberGlow  },
  { char: "I", color: T.green, glow: T.greenGlow  },
  { char: "G", color: T.red,   glow: T.redGlow    },
  { char: "_", color: T.amber, glow: T.amberGlow  },
  { char: "1", color: T.green, glow: T.greenGlow  },
];

function BrandMark() {
  return (
    <div className="brand-mark">
      <span className="brand-icon">◈</span>
      <div className="brand-letters">
        {BRAND_LETTERS.map(({ char, color, glow }, i) => (
          <div key={i} className="brand-cell">
            <span className="brand-char" style={{ color, textShadow: `0 0 8px ${glow}` }}>
              {char}
            </span>
            <div className="brand-lamp" style={{ background: color, boxShadow: `0 0 5px ${glow}` }} />
          </div>
        ))}
      </div>
      <span className="brand-sub">Smart Signal Management System</span>
      <style>{`
        .brand-mark { display:flex; align-items:center; gap:8px; flex-shrink:0; }
        .brand-icon { font-size:14px; color:${T.amber}; filter:drop-shadow(0 0 5px ${T.amberGlow}); line-height:1; flex-shrink:0; }
        .brand-letters { display:flex; gap:2px; align-items:flex-end; }
        .brand-cell { display:flex; flex-direction:column; align-items:center; gap:2px; background:#27272a; border:1px solid #3f3f46; padding:2px 4px 3px; border-radius:2px; }
        .brand-char { font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:800; letter-spacing:0; line-height:1; }
        .brand-lamp { width:4px; height:4px; border-radius:50%; }
        .brand-sub { font-family:'JetBrains Mono',monospace; font-size:7px; color:#52525b; letter-spacing:0.06em; display:none; }
        @media (min-width:1200px) { .brand-sub { display:inline; } }
      `}</style>
    </div>
  );
}

function StatusPill({ label, value, color = "#71717a", glow = false }: {
  label: string; value: string; color?: string; glow?: boolean;
}) {
  return (
    <div className="sp">
      <span className="sp-label">{label}</span>
      <span className="sp-value" style={{ color, textShadow: glow ? `0 0 8px ${color}` : "none" }}>{value}</span>
      <style>{`
        .sp { display:flex; align-items:center; gap:5px; background:#27272a; border:1px solid #3f3f46; padding:3px 10px; border-radius:3px; flex-shrink:0; }
        .sp-label { font-family:'JetBrains Mono',monospace; font-size:8px; color:#52525b; letter-spacing:0.1em; font-weight:700; }
        .sp-value { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:800; }
      `}</style>
    </div>
  );
}

function TopbarSignal({ isRunning, isLive }: { isRunning: boolean; isLive: boolean }) {
  return (
    <div className="tb-signal">
      {[
        { c: T.red,   active: !isRunning },
        { c: T.amber, active: isRunning && !isLive },
        { c: T.green, active: isRunning && isLive  },
      ].map(({ c, active }, i) => (
        <div key={i} className="tb-signal-dot" style={{
          background: active ? c : `${c}25`,
          boxShadow: active ? `0 0 8px ${c}88` : "none",
          animation: active && c === T.green ? "signal-pulse 2s ease-in-out infinite" :
                     active && c === T.amber ? "amber-pulse 1.5s ease-in-out infinite" :
                     active && c === T.red   ? "red-pulse 1s ease-in-out infinite" : "none",
        }} />
      ))}
      <style>{`
        .tb-signal { display:flex; flex-direction:column; gap:3px; padding:5px 7px; background:#27272a; border:1px solid #3f3f46; border-radius:4px; flex-shrink:0; }
        .tb-signal-dot { width:7px; height:7px; border-radius:50%; transition:all 0.3s; }
      `}</style>
    </div>
  );
}

// ── Top Bar ───────────────────────────────────────────────────────────────────
function TopBar() {
  const { connectionStatus, isLive, isRunning, syncDiff } = useWebSocket();
  const { baseline } = useTrafficStore();

  const connColor =
    connectionStatus === "connected"  ? T.green :
    connectionStatus === "connecting" ? T.amber  : T.red;
  const connLabel =
    connectionStatus === "connected"  ? "CONNECTED" :
    connectionStatus === "connecting" ? "CONNECTING…" : "OFFLINE";

  return (
    <header className="top-bar">
      <BrandMark />
      <div className="tb-sep" />
      <div className="tb-pills">
        <StatusPill label="STATUS" value={isRunning ? "RUNNING" : "IDLE"} color={isRunning ? T.green : "#71717a"} glow={isRunning} />
        <StatusPill label="RL ALGO" value="D-DQN" color={T.amber} />
        <StatusPill label="STEP"   value={baseline?.step?.toLocaleString() ?? "—"} />
        <StatusPill label="SYNC"   value={`${(syncDiff ?? 0).toFixed(3)}s`} color={(syncDiff ?? 0) < 0.1 ? T.green : T.amber} />
        {isRunning && <PerformanceBadge />}
      </div>
      <TopbarSignal isRunning={isRunning} isLive={isLive} />
      <div className="tb-conn">
        <div className="tb-conn-dot" style={{ background: connColor, boxShadow: `0 0 8px ${connColor}88` }} />
        <span className="tb-conn-label" style={{ color: connColor }}>{connLabel}</span>
      </div>
      <style>{`
        .top-bar {
          height: 50px;
          background: #18181b;
          border-top: 2px solid transparent;
          border-bottom: 3px solid transparent;
          border-image: linear-gradient(90deg, ${T.red} 0%, ${T.red} 33.3%, ${T.amber} 33.3%, ${T.amber} 66.6%, ${T.green} 66.6%, ${T.green} 100%) 1;
          display: flex;
          align-items: center;
          padding: 0 18px;
          gap: 12px;
          flex-shrink: 0;
        }
        .tb-sep { width:1px; height:26px; background:#3f3f46; flex-shrink:0; }
        .tb-pills { display:flex; gap:5px; flex:1; align-items:center; flex-wrap:wrap; }
        .tb-conn { display:flex; align-items:center; gap:7px; flex-shrink:0; margin-left:8px; }
        .tb-conn-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
        .tb-conn-label { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; letter-spacing:0.1em; }
      `}</style>
    </header>
  );
}

export function SectionHeader({ title, sub, accentColor }: {
  title: string; sub?: string; accentColor: string;
}) {
  return (
    <div className="sh">
      <div className="sh-bar" style={{ background: accentColor, boxShadow: `0 0 6px ${accentColor}66` }} />
      <span className="sh-title" style={{ color: accentColor }}>{title}</span>
      {sub && <span className="sh-sub">{sub}</span>}
      <style>{`
        .sh { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid #e2ddd5; background:#fff; flex-shrink:0; }
        .sh-bar { width:3px; height:14px; border-radius:2px; flex-shrink:0; }
        .sh-title { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:800; letter-spacing:0.14em; }
        .sh-sub { font-family:'JetBrains Mono',monospace; font-size:8px; color:#a1a1aa; letter-spacing:0.08em; }
      `}</style>
    </div>
  );
}

function ErrorToast({ msg, onDismiss }: { msg: string; onDismiss: () => void }) {
  return (
    <div className="et" onClick={onDismiss}>
      <span style={{ color: T.red, fontSize: "0.8rem" }}>⚠</span>
      <span className="et-msg">{msg}</span>
      <span style={{ color: `${T.red}66`, fontSize: "0.65rem" }}>✕</span>
      <style>{`
        .et { position:fixed; bottom:1rem; left:50%; transform:translateX(-50%); display:flex; align-items:center; gap:0.6rem; padding:0.6rem 1rem; background:#fff; border:1px solid rgba(220,38,38,0.4); box-shadow:0 4px 20px rgba(220,38,38,0.15); cursor:pointer; z-index:1000; animation:slide-up 0.2s ease; max-width:440px; border-radius:4px; }
        .et-msg { font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:${T.red}; flex:1; line-height:1.5; }
      `}</style>
    </div>
  );
}

export default function MainDashboard() {
  const { isRunning, setIsRunning, resetHistory, setTrafficLights } = useTrafficStore();
  const [globalError, setGlobalError] = useState<string | null>(null);

  const handleStart = async () => {
    try {
      await startSimulation();
      const tls = await getTrafficLights();
      setTrafficLights(tls);
      setIsRunning(true);
    } catch (e) {
      setGlobalError(e instanceof Error ? e.message : "Failed to start");
    }
  };

  const handleStop = async () => {
    try {
      await stopSimulation();
      setIsRunning(false);
      resetHistory();
    } catch (e) {
      setGlobalError(e instanceof Error ? e.message : "Failed to stop");
    }
  };

  useKeyboardShortcuts(handleStart, handleStop);

  return (
    <div className="dashboard">
      <TopBar />
      {isRunning && <StatsCards />}

      <div className="dashboard-body">
        <aside className="panel-left">
          <SectionHeader title="CONTROL" sub="simulation settings" accentColor={T.red} />
          <div className="left-scroll">
            <div className="left-section">
              <NetworkSelector disabled={isRunning} />
            </div>
            <div className="left-divider" />
            <ControlPanel />
            {isRunning && (
              <>
                <div className="left-divider" />
                <div className="left-section recorder-section">
                  <SessionRecorder />
                </div>
              </>
            )}
          </div>
        </aside>

        <main className="panel-center">
          <SectionHeader title="METRICS" sub="live comparison — baseline vs rl agent" accentColor={T.amber} />
          <div className="center-scroll">
            <MetricsComparison />
          </div>
        </main>

        <aside className="panel-right">
          <SectionHeader title="LIVE DATA" sub="real-time readout" accentColor={T.green} />
          <div className="right-scroll">
            <LiveComparison />
          </div>
        </aside>
      </div>

      {globalError && <ErrorToast msg={globalError} onDismiss={() => setGlobalError(null)} />}

      <style>{`
        .dashboard { display:flex; flex-direction:column; height:100vh; overflow:hidden; background:#f7f6f1; }
        .dashboard-body { display:grid; grid-template-columns:224px 1fr 292px; flex:1; overflow:hidden; min-height:0; }
        .panel-left  { display:flex; flex-direction:column; border-right:1px solid #e2ddd5; background:#f2f1ec; overflow:hidden; }
        .panel-center { display:flex; flex-direction:column; border-right:1px solid #e2ddd5; background:#f7f6f1; overflow:hidden; }
        .panel-right  { display:flex; flex-direction:column; background:#f2f1ec; overflow:hidden; }
        .left-scroll  { flex:1; overflow-y:auto; display:flex; flex-direction:column; }
        .center-scroll { flex:1; overflow-y:auto; min-height:0; }
        .right-scroll  { flex:1; overflow-y:auto; min-height:0; }
        .left-section { padding:0.65rem 0.75rem; }
        .left-divider { height:1px; background:#e2ddd5; flex-shrink:0; }
        .recorder-section { margin-top:auto; }
        @media (max-width:900px) {
          .dashboard-body { grid-template-columns:1fr; }
          .panel-left  { border-right:none; border-bottom:1px solid #e2ddd5; }
          .panel-center { border-right:none; border-bottom:1px solid #e2ddd5; }
        }
      `}</style>
    </div>
  );
}