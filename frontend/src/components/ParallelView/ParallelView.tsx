// components/ParallelView/ParallelView.tsx
import { useState, useEffect } from 'react';
import { useTrafficStore } from "../../store/TrafficStore";
import SimulationCanvas from "../SimulationCanvas/SimulationCanvas";
import type { SimulationState } from "../../types";

function MetricBar({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: number | undefined;
  unit: string;
  accent: string;
}) {
  return (
    <div className="metric-bar">
      <span className="mb-label">{label}</span>
      <span className="mb-value" style={{ color: accent }}>
        {value !== undefined ? value.toFixed(2) : "—"}
        <span className="mb-unit"> {unit}</span>
      </span>
      <style>{`
        .metric-bar {
          display: flex; justify-content: space-between; align-items: baseline;
          padding: 0.28rem 0.75rem;
          border-bottom: 1px solid #1e2128;
        }
        .metric-bar:last-child { border-bottom: none; }
        .mb-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; color: #4a5060;
          font-weight: 700; letter-spacing: 0.08em;
        }
        .mb-value {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.72rem; font-weight: 700;
        }
        .mb-unit { font-size: 0.55rem; color: #4a5060; font-weight: 400; }
      `}</style>
    </div>
  );
}

function SimPanel({
  state,
  label,
  accent,
  tag,
  networkType,
}: {
  state: SimulationState | null;
  label: string;
  accent: string;
  tag: string;
  networkType?: string;
}) {
  const m = state?.metrics;

  return (
    <div className="sim-panel">
      {/* Header */}
      <div className="sp-header" style={{ borderColor: accent + "44" }}>
        <span className="sp-tag" style={{ background: accent + "18", color: accent, borderColor: accent + "44" }}>
          {tag}
        </span>
        <span className="sp-label">{label}</span>
        <span className={`sp-status ${state ? "active" : ""}`} style={state ? { color: accent } : {}}>
          {state ? "● LIVE" : "○ IDLE"}
        </span>
      </div>

      <SimulationCanvas state={state} accent={accent} networkType={networkType} />

      {/* Metrics footer */}
      <div className="sp-metrics">
        <MetricBar label="AVG SPEED"    value={m?.avg_speed}         unit="m/s" accent={accent} />
        <MetricBar label="AVG WAITING"  value={m?.avg_waiting_time}  unit="s"   accent={accent} />
        <MetricBar label="QUEUE LEN"    value={m?.queue_length}      unit="veh" accent={accent} />
        <MetricBar label="THROUGHPUT"   value={m?.throughput}        unit="v/s" accent={accent} />
      </div>

      <style>{`
        .sim-panel {
          display: flex; flex-direction: column;
          background: #12141a;
          border: 1px solid #1e2128;
          overflow: hidden;
        }
        .sp-header {
          display: flex; align-items: center; gap: 0.6rem;
          padding: 0.5rem 0.75rem;
          border-bottom: 1px solid;
          background: #0e1015;
        }
        .sp-tag {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.55rem; font-weight: 800;
          letter-spacing: 0.15em;
          padding: 0.15rem 0.45rem;
          border: 1px solid;
        }
        .sp-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.62rem; color: #7a8090;
          font-weight: 600; letter-spacing: 0.06em; flex: 1;
        }
        .sp-status {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; font-weight: 700;
          color: #3a3f4d; letter-spacing: 0.1em;
        }
        .sp-status.active { animation: livepulse 2s ease-in-out infinite; }
        @keyframes livepulse { 0%,100%{opacity:1} 50%{opacity:.5} }
        .sp-metrics { background: #0e1015; }
      `}</style>
    </div>
  );
}

export default function ParallelView() {
  const { baseline, rl } = useTrafficStore();
  const [currentNetwork, setCurrentNetwork] = useState<string>('simple_intersection');

  useEffect(() => {
    const fetchCurrentNetwork = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/simulation/networks');
        const data = await response.json();
        setCurrentNetwork(data.current);
      } catch (error) {
        console.error('Failed to fetch current network:', error);
      }
    };
    
    fetchCurrentNetwork();
  }, [baseline?.step, rl?.step]);

  return (
    <div className="parallel-view">
      <SimPanel
        state={baseline}
        label="FIXED-TIME BASELINE CONTROLLER"
        accent="#00e676"
        tag="BASE"
        networkType={currentNetwork}
      />
      <SimPanel
        state={rl}
        label="REINFORCEMENT LEARNING AGENT"
        accent="#4fc3f7"
        tag="RL"
        networkType={currentNetwork}
      />

      <style>{`
        .parallel-view {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.5rem;
          width: 100%;
        }
        @media (max-width: 800px) {
          .parallel-view { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}