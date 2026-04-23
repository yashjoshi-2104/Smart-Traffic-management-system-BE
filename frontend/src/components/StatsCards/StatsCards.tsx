// components/StatsCards/StatsCards.tsx
import { useTrafficStore } from "../../store/TrafficStore";

interface KpiProps {
  label: string;
  baseline: number;
  rl: number;
  unit: string;
  decimals?: number;
  lowerIsBetter?: boolean;
}

function KpiCard({ label, baseline, rl, unit, decimals = 1, lowerIsBetter = true }: KpiProps) {
  const delta   = baseline > 0 ? ((rl - baseline) / baseline) * 100 : 0;
  const neutral = Math.abs(delta) < 0.5;
  const improved = lowerIsBetter ? delta < 0 : delta > 0;
  const color   = neutral ? "#a1a1aa" : improved ? "#15803d" : "#b91c1c";
  const borderTop = neutral ? "#e2ddd5" : improved ? "#15803d" : "#b91c1c";

  return (
    <div className="kpi" style={{ borderTopColor: borderTop }}>
      <span className="kpi-label">{label.toUpperCase()}</span>
      <span className="kpi-delta" style={{ color }}>
        {neutral ? "—" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`}
      </span>
      <div className="kpi-row">
        <div className="kpi-side">
          <span className="kpi-side-label">BASELINE</span>
          <span className="kpi-side-val" style={{ color: "#1d4ed8" }}>
            {baseline.toFixed(decimals)}{unit}
          </span>
        </div>
        <div className="kpi-divider" />
        <div className="kpi-side">
          <span className="kpi-side-label">RL AGENT</span>
          <span className="kpi-side-val" style={{ color: "#15803d" }}>
            {rl.toFixed(decimals)}{unit}
          </span>
        </div>
      </div>
      <style>{`
        .kpi {
          background: #fff;
          border: 1px solid #e2ddd5;
          border-top: 3px solid;
          padding: 12px 16px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          transition: border-top-color 0.4s ease;
          animation: fade-in 0.3s ease;
        }
        .kpi-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 8px;
          font-weight: 700;
          letter-spacing: 0.14em;
          color: #71717a;
        }
        .kpi-delta {
          font-family: 'JetBrains Mono', monospace;
          font-size: 26px;
          font-weight: 800;
          line-height: 1;
          letter-spacing: -0.02em;
          transition: color 0.3s;
        }
        .kpi-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 2px;
        }
        .kpi-side { display:flex; flex-direction:column; gap:1px; flex:1; }
        .kpi-side-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 7px;
          font-weight: 600;
          letter-spacing: 0.1em;
          color: #a1a1aa;
        }
        .kpi-side-val {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11px;
          font-weight: 700;
        }
        .kpi-divider { width:1px; height:24px; background:#e2ddd5; flex-shrink:0; }
      `}</style>
    </div>
  );
}

export default function StatsCards() {
  const { metricsHistory: h } = useTrafficStore();

  const bWait  = h.baseline.avg_waiting_time.at(-1) ?? 0;
  const rWait  = h.rl.avg_waiting_time.at(-1)       ?? 0;
  const bSpeed = h.baseline.avg_speed.at(-1)        ?? 0;
  const rSpeed = h.rl.avg_speed.at(-1)              ?? 0;
  const bQueue = h.baseline.queue_length.at(-1)     ?? 0;
  const rQueue = h.rl.queue_length.at(-1)           ?? 0;
  const bThru  = h.baseline.throughput.at(-1)       ?? 0;
  const rThru  = h.rl.throughput.at(-1)             ?? 0;

  return (
    <div className="stats-strip">
      <KpiCard label="Avg Wait Time"  baseline={bWait}  rl={rWait}  unit="s"    decimals={1} lowerIsBetter={true}  />
      <KpiCard label="Avg Speed"      baseline={bSpeed} rl={rSpeed} unit=" m/s" decimals={2} lowerIsBetter={false} />
      <KpiCard label="Queue Length"   baseline={bQueue} rl={rQueue} unit=" veh" decimals={0} lowerIsBetter={true}  />
      <KpiCard label="Throughput"     baseline={bThru}  rl={rThru}  unit=" veh" decimals={0} lowerIsBetter={false} />
      <style>{`
        .stats-strip {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          border-bottom: 1px solid #e2ddd5;
          flex-shrink: 0;
          background: #f7f6f1;
        }
        .stats-strip .kpi { border-radius:0; border-left:none; border-bottom:none; }
        .stats-strip .kpi:not(:last-child) { border-right:1px solid #e2ddd5; }
      `}</style>
    </div>
  );
}