// components/LiveComparison/LiveComparison.tsx
import { useTrafficStore } from "../../store/TrafficStore";

const T = {
  red:      "#dc2626",
  redBg:    "rgba(220,38,38,0.08)",
  redGlow:  "rgba(220,38,38,0.3)",
  amber:    "#f59e0b",
  amberBg:  "rgba(245,158,11,0.08)",
  green:    "#16a34a",
  greenGlow:"rgba(22,163,74,0.3)",
};

// ── Mini traffic signal widget ────────────────────────────────────────────────
// EASTER EGG: used in emergency section — all dim = clear, red lit = emergency
function TrafficSignal({ activeColor }: { activeColor?: string }) {
  const dots = [
    { c: T.red,   glow: T.redGlow   },
    { c: T.amber, glow: "rgba(245,158,11,0.4)" },
    { c: T.green, glow: T.greenGlow },
  ];
  return (
    <div className="ts-wrap">
      {dots.map(({ c, glow }, i) => {
        const on = c === activeColor;
        return (
          <div key={i} className="ts-dot" style={{
            background: on ? c : `${c}25`,
            boxShadow:  on ? `0 0 7px ${glow}` : "none",
            animation:  on && c === T.red ? "red-pulse 1s ease-in-out infinite" : "none",
          }} />
        );
      })}
      <style>{`
        .ts-wrap { display:flex; gap:3px; align-items:center; }
        .ts-dot { width:7px; height:7px; border-radius:50%; transition:all 0.3s; }
      `}</style>
    </div>
  );
}

// ── Delta badge ───────────────────────────────────────────────────────────────
function Delta({ baseline, rl, lowerIsBetter = true }: {
  baseline: number; rl: number; lowerIsBetter?: boolean;
}) {
  if (baseline === 0) return <span className="delta neutral">—</span>;
  const pct = ((rl - baseline) / baseline) * 100;
  const improved = lowerIsBetter ? pct < 0 : pct > 0;
  return (
    <span className={`delta ${improved ? "good" : "bad"}`}>
      {improved ? "▼" : "▲"} {Math.abs(pct).toFixed(1)}%
    </span>
  );
}

// ── Metric row ────────────────────────────────────────────────────────────────
function Row({ label, baseline, rl, unit = "", lowerIsBetter = true, decimals = 1 }: {
  label: string; baseline: number; rl: number;
  unit?: string; lowerIsBetter?: boolean; decimals?: number;
}) {
  return (
    <div className="lv-row">
      <span className="lv-label">{label}</span>
      <span className="lv-base">{baseline.toFixed(decimals)}{unit}</span>
      <span className="lv-rl">{rl.toFixed(decimals)}{unit}</span>
      <Delta baseline={baseline} rl={rl} lowerIsBetter={lowerIsBetter} />
    </div>
  );
}

// ── Emergency panel ───────────────────────────────────────────────────────────
function EmergencyPanel({ emergency }: { emergency: any }) {
  const b = emergency?.baseline;
  const r = emergency?.rl;
  const hasEmergency = b?.has_emergency || r?.has_emergency;

  return (
    <div className={`ep ${hasEmergency ? "ep-active" : ""}`}>
      <div className="ep-header">
        {/* EASTER EGG: traffic signal — red when active, all dim when clear */}
        <TrafficSignal activeColor={hasEmergency ? T.red : undefined} />
        <span className="ep-title">EMERGENCY</span>
        {hasEmergency && <span className="ep-badge">ACTIVE</span>}
      </div>
      {hasEmergency ? (
        <div className="ep-body">
          {b?.has_emergency && (
            <div className="ep-row">
              <span className="ep-side" style={{ color:"#1d4ed8" }}>BASE</span>
              <span className="ep-info">
                {b.count} vehicle{b.count !== 1 ? "s" : ""} ·{" "}
                {Object.entries(b.by_direction || {}).filter(([,v]) => (v as number) > 0).map(([d]) => d.toUpperCase()).join(", ")}
              </span>
            </div>
          )}
          {r?.has_emergency && (
            <div className="ep-row">
              <span className="ep-side" style={{ color:"#15803d" }}>RL</span>
              <span className="ep-info" style={{ color:"#15803d" }}>
                {r.count} vehicle{r.count !== 1 ? "s" : ""} ·{" "}
                {Object.entries(r.by_direction || {}).filter(([,v]) => (v as number) > 0).map(([d]) => d.toUpperCase()).join(", ")}
              </span>
            </div>
          )}
        </div>
      ) : (
        <span className="ep-clear">No active emergency vehicles</span>
      )}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function LiveComparison() {
  const { baseline, rl, isRunning, emergency } = useTrafficStore();
  const bm = baseline?.metrics;
  const rm = rl?.metrics;

  if (!isRunning || !bm || !rm) {
    return (
      <div className="lv-idle">
        <span className="lv-idle-icon">◈</span>
        <span className="lv-idle-text">Start simulation to see live data</span>
        <style>{liveStyles}</style>
      </div>
    );
  }

  return (
    <div className="lv-wrap">
      {/* Column headers */}
      <div className="lv-thead">
        <span className="lv-th">METRIC</span>
        <span className="lv-th center" style={{ color:"#1d4ed8" }}>
          <span className="lv-th-dot" style={{ background:"#1d4ed8" }} /> BASE
        </span>
        <span className="lv-th center" style={{ color:"#15803d" }}>
          <span className="lv-th-dot" style={{ background:"#15803d" }} /> RL
        </span>
        <span className="lv-th center" style={{ color:"#a1a1aa" }}>Δ</span>
      </div>

      <div className="lv-body">
        <div className="lv-section">PERFORMANCE</div>
        <Row label="Wait time"  baseline={bm.avg_waiting_time} rl={rm.avg_waiting_time} unit="s"    lowerIsBetter={true}  decimals={1} />
        <Row label="Speed"      baseline={bm.avg_speed}        rl={rm.avg_speed}        unit=" m/s" lowerIsBetter={false} decimals={2} />
        <Row label="Queue"      baseline={bm.queue_length}     rl={rm.queue_length}     unit=" veh" lowerIsBetter={true}  decimals={0} />
        <Row label="Throughput" baseline={bm.throughput}       rl={rm.throughput}       unit=""     lowerIsBetter={false} decimals={0} />
        <Row label="Stopped"    baseline={bm.stopped_ratio ?? 0} rl={rm.stopped_ratio ?? 0} unit="%" lowerIsBetter={true} decimals={1} />

        <div className="lv-section" style={{ marginTop:"6px" }}>VEHICLES</div>
        <div className="lv-row">
          <span className="lv-label">Active in sim</span>
          <span className="lv-base">{bm.vehicle_count ?? 0}</span>
          <span className="lv-rl">{rm.vehicle_count ?? 0}</span>
          <span />
        </div>
      </div>

      <EmergencyPanel emergency={emergency} />
      <style>{liveStyles}</style>
    </div>
  );
}

const liveStyles = `
  .lv-idle {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    height:220px; gap:10px; opacity:0.25;
  }
  .lv-idle-icon { font-size:2rem; color:#f59e0b; }
  .lv-idle-text { font-family:'JetBrains Mono',monospace; font-size:9px; color:#71717a; letter-spacing:0.08em; text-align:center; }

  .lv-wrap { display:flex; flex-direction:column; }

  /* Headers */
  .lv-thead {
    display:grid; grid-template-columns:1fr 56px 56px 50px;
    align-items:center; padding:8px 14px 6px;
    background:#fff; border-bottom:2px solid #e2ddd5;
    position:sticky; top:0; z-index:1;
  }
  .lv-th {
    font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700;
    letter-spacing:0.1em; color:#a1a1aa;
  }
  .lv-th.center { display:flex; align-items:center; justify-content:center; gap:4px; }
  .lv-th-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }

  /* Body */
  .lv-body { padding:0 14px; display:flex; flex-direction:column; }
  .lv-section {
    font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700;
    letter-spacing:0.16em; color:#a1a1aa; padding:10px 0 4px;
  }

  .lv-row {
    display:grid; grid-template-columns:1fr 56px 56px 50px;
    align-items:center; padding:7px 0;
    border-bottom:1px solid #f2f1ec;
    transition:background 0.1s;
  }
  .lv-row:hover { background:#fafaf7; margin:0 -14px; padding-left:14px; padding-right:14px; }

  .lv-label { font-family:'Outfit',sans-serif; font-size:12px; color:#3f3f46; font-weight:400; }
  .lv-base  { font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:#1d4ed8; text-align:center; }
  .lv-rl    { font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:#15803d; text-align:center; }

  /* Delta */
  .delta {
    font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700;
    letter-spacing:0.04em; text-align:center; padding:2px 4px; border-radius:3px;
  }
  .delta.good    { color:#15803d; background:#dcfce7; }
  .delta.bad     { color:#b91c1c; background:#fef2f2; }
  .delta.neutral { color:#a1a1aa; }

  /* Emergency panel — EASTER EGG: red when active */
  .ep {
    margin:12px 14px 14px;
    border:1px solid #e2ddd5; border-radius:6px;
    background:#fff; transition:all 0.3s;
  }
  .ep.ep-active {
    border-color:rgba(220,38,38,0.4);
    background:rgba(220,38,38,0.03);
    box-shadow:0 0 12px rgba(220,38,38,0.08);
  }
  .ep-header {
    display:flex; align-items:center; gap:8px;
    padding:10px 12px; border-bottom:1px solid #e2ddd5;
  }
  .ep.ep-active .ep-header { border-bottom-color:rgba(220,38,38,0.2); }
  .ep-title {
    font-family:'JetBrains Mono',monospace; font-size:9px;
    font-weight:800; letter-spacing:0.12em; color:#a1a1aa; flex:1;
  }
  .ep.ep-active .ep-title { color:${T.red}; }
  .ep-badge {
    font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700;
    letter-spacing:0.1em; color:${T.red}; background:rgba(220,38,38,0.1);
    padding:2px 6px; border:1px solid rgba(220,38,38,0.3); border-radius:2px;
  }
  .ep-body { padding:8px 12px; display:flex; flex-direction:column; gap:5px; }
  .ep-row  { display:flex; align-items:center; gap:7px; }
  .ep-side { font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700; min-width:28px; }
  .ep-info { font-family:'Outfit',sans-serif; font-size:12px; color:#3f3f46; }
  .ep-clear { padding:10px 12px; font-family:'Outfit',sans-serif; font-size:12px; color:#a1a1aa; }
`;