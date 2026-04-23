// components/MetricsComparison/SummaryStats.tsx
import { useTrafficStore } from "../../store/TrafficStore";

interface StatRowProps {
  label: string;
  baseVal: number | undefined;
  rlVal:   number | undefined;
  unit:    string;
  higherIsBetter: boolean;
  decimals?: number;
}

function StatRow({ label, baseVal, rlVal, unit, higherIsBetter, decimals = 2 }: StatRowProps) {
  const bStr = baseVal !== undefined ? baseVal.toFixed(decimals) : "—";
  const rStr = rlVal   !== undefined ? rlVal.toFixed(decimals)   : "—";

  const delta =
    baseVal !== undefined && rlVal !== undefined && baseVal !== 0
      ? ((rlVal - baseVal) / Math.abs(baseVal)) * 100
      : null;

  const rlWins =
    delta !== null && (higherIsBetter ? delta > 0 : delta < 0);

  return (
    <div className="sr-row">
      <span className="sr-label">{label}</span>

      <span className="sr-base">
        {bStr}<span className="sr-unit"> {unit}</span>
      </span>

      <span className={`sr-rl ${delta !== null ? (rlWins ? "win" : "lose") : ""}`}>
        {rStr}<span className="sr-unit"> {unit}</span>
      </span>

      <span className="sr-delta-cell">
        {delta !== null ? (
          <span className={`sr-badge ${rlWins ? "win" : "lose"}`}>
            {delta >= 0 ? "+" : ""}{delta.toFixed(1)}%
          </span>
        ) : (
          <span className="sr-badge-na">—</span>
        )}
      </span>

      <style>{`
        .sr-row {
          display: grid;
          grid-template-columns: 1fr 80px 80px 64px;
          align-items: center;
          padding: 0.32rem 0.75rem;
          border-bottom: 1px solid #1a1d25;
        }
        .sr-row:last-child { border-bottom: none; }
        .sr-row:hover { background: rgba(255,255,255,0.015); }
        .sr-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; color: #4a5060;
          font-weight: 700; letter-spacing: 0.07em;
        }
        .sr-base, .sr-rl {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.68rem; font-weight: 700;
          text-align: right; color: #7a8090;
        }
        .sr-rl.win  { color: #4fc3f7; }
        .sr-rl.lose { color: #ff7070; }
        .sr-unit { font-size: 0.54rem; color: #3a3f4d; font-weight: 400; }
        .sr-delta-cell { text-align: right; }
        .sr-badge {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; font-weight: 700;
          padding: 0.1rem 0.3rem;
          display: inline-block;
        }
        .sr-badge.win  { color: #00e676; background: rgba(0,230,118,0.1); }
        .sr-badge.lose { color: #ff3255; background: rgba(255,50,80,0.1); }
        .sr-badge-na { color: #2e3240; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; }
      `}</style>
    </div>
  );
}

export default function SummaryStats() {
  const { baseline, rl } = useTrafficStore();
  const bm = baseline?.metrics;
  const rm = rl?.metrics;

  const rows: StatRowProps[] = [
    {
      label: "AVG SPEED",
      baseVal: bm?.avg_speed,
      rlVal:   rm?.avg_speed,
      unit: "m/s", higherIsBetter: true,
    },
    {
      label: "AVG WAITING",
      baseVal: bm?.avg_waiting_time,
      rlVal:   rm?.avg_waiting_time,
      unit: "s", higherIsBetter: false,
    },
    {
      label: "QUEUE LENGTH",
      baseVal: bm?.queue_length,
      rlVal:   rm?.queue_length,
      unit: "veh", higherIsBetter: false, decimals: 0,
    },
    {
      label: "THROUGHPUT",
      baseVal: bm?.throughput,
      rlVal:   rm?.throughput,
      unit: "v/s", higherIsBetter: true,
    },
    {
      label: "STOPPED %",
      baseVal: bm ? bm.stopped_ratio * 100 : undefined,
      rlVal:   rm ? rm.stopped_ratio * 100 : undefined,
      unit: "%", higherIsBetter: false, decimals: 1,
    },
    {
      label: "VEHICLES",
      baseVal: bm?.vehicle_count,
      rlVal:   rm?.vehicle_count,
      unit: "", higherIsBetter: true, decimals: 0,
    },
  ];

  return (
    <div className="summary-stats">
      {/* Column headers */}
      <div className="ss-head">
        <span className="ss-head-label">METRIC</span>
        <span className="ss-head-col" style={{ color: "#00e676" }}>BASELINE</span>
        <span className="ss-head-col" style={{ color: "#4fc3f7" }}>RL AGENT</span>
        <span className="ss-head-col">DELTA</span>
      </div>

      {rows.map((r) => (
        <StatRow key={r.label} {...r} />
      ))}

      {/* RL win summary */}
      {bm && rm && (
        <div className="ss-footer">
          <RlScoreBadge bm={bm} rm={rm} />
        </div>
      )}

      <style>{`
        .summary-stats {
          background: #0e1015;
          border: 1px solid #1e2128;
          overflow: hidden;
        }
        .ss-head {
          display: grid;
          grid-template-columns: 1fr 80px 80px 64px;
          padding: 0.35rem 0.75rem;
          background: #12141a;
          border-bottom: 1px solid #1e2128;
        }
        .ss-head-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.54rem; font-weight: 700;
          letter-spacing: 0.12em; color: #3a3f4d;
        }
        .ss-head-col {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.54rem; font-weight: 700;
          letter-spacing: 0.1em; color: #3a3f4d;
          text-align: right;
        }
        .ss-footer {
          padding: 0.5rem 0.75rem;
          border-top: 1px solid #1e2128;
          background: #12141a;
        }
      `}</style>
    </div>
  );
}

// ── RL score badge ─────────────────────────────────────────────────────────
function RlScoreBadge({
  bm,
  rm,
}: {
  bm: NonNullable<ReturnType<typeof useTrafficStore>["baseline"]>["metrics"];
  rm: NonNullable<ReturnType<typeof useTrafficStore>["rl"]>["metrics"];
}) {
  const checks = [
    rm.avg_speed         > bm.avg_speed,
    rm.avg_waiting_time  < bm.avg_waiting_time,
    rm.queue_length      < bm.queue_length,
    rm.throughput        > bm.throughput,
    rm.stopped_ratio     < bm.stopped_ratio,
  ];
  const wins = checks.filter(Boolean).length;
  const total = checks.length;
  const pct   = Math.round((wins / total) * 100);

  return (
    <div className="rl-score">
      <span className="rl-score-label">RL PERFORMANCE</span>
      <div className="rl-score-bar-wrap">
        <div
          className="rl-score-bar"
          style={{ width: `${pct}%`, background: pct >= 60 ? "#00e676" : pct >= 40 ? "#ffaa00" : "#ff3255" }}
        />
      </div>
      <span
        className="rl-score-val"
        style={{ color: pct >= 60 ? "#00e676" : pct >= 40 ? "#ffaa00" : "#ff3255" }}
      >
        {wins}/{total} metrics
      </span>
      <style>{`
        .rl-score { display: flex; align-items: center; gap: 0.6rem; }
        .rl-score-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.55rem; color: #3a3f4d;
          font-weight: 700; letter-spacing: 0.1em; white-space: nowrap;
        }
        .rl-score-bar-wrap {
          flex: 1; height: 4px; background: #1e2128;
        }
        .rl-score-bar { height: 100%; transition: width 0.5s ease; }
        .rl-score-val {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.62rem; font-weight: 800; white-space: nowrap;
        }
      `}</style>
    </div>
  );
}