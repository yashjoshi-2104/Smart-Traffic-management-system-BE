// components/MetricsComparison/MetricsComparison.tsx
import WaitingTimeChart from "./WaitingTimeChart";
import QueueLengthChart from "./QueueLengthChart";
import { useTrafficStore } from "../../store/TrafficStore";
import { useEffect, useRef } from "react";
import {
  Chart, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, Filler, Tooltip,
} from "chart.js";

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip);

// ── Reusable line chart ───────────────────────────────────────────────────────
function LineChart({
  title, baseData, rlData, unit, higherIsBetter, height = 110,
}: {
  title: string; baseData: number[]; rlData: number[];
  unit: string; higherIsBetter: boolean; height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef  = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;
    chartRef.current = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label:"Baseline", data:[], borderColor:"#1d4ed8", backgroundColor:"rgba(29,78,216,0.06)", borderWidth:1.5, pointRadius:0, fill:true, tension:0.4 },
          { label:"RL Agent", data:[], borderColor:"#15803d", backgroundColor:"rgba(21,128,61,0.06)",  borderWidth:1.5, pointRadius:0, fill:true, tension:0.4 },
        ],
      },
      options: {
        responsive:true, maintainAspectRatio:false, animation:false,
        interaction:{ mode:"index", intersect:false },
        plugins:{
          legend:{ display:false },
          tooltip:{
            backgroundColor:"#fff", borderColor:"#e2ddd5", borderWidth:1,
            titleColor:"#71717a", bodyColor:"#3f3f46",
            bodyFont:{ family:"'JetBrains Mono',monospace", size:11 },
            titleFont:{ family:"'JetBrains Mono',monospace", size:10 },
            callbacks:{ label:(i) => ` ${i.dataset.label}: ${(i.raw as number).toFixed(2)} ${unit}` },
          },
        },
        scales:{
          x:{ display:false },
          y:{
            position:"right",
            grid:{ color:"#f2f1ec", lineWidth:1 },
            border:{ color:"#e2ddd5" },
            ticks:{ color:"#a1a1aa", font:{ family:"'JetBrains Mono',monospace", size:9 }, maxTicksLimit:4 },
          },
        },
      },
    });
    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, [unit]);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.data.labels           = baseData.map((_,i) => i.toString());
    chartRef.current.data.datasets[0].data = baseData;
    chartRef.current.data.datasets[1].data = rlData;
    chartRef.current.update("none");
  }, [baseData, rlData]);

  const lastBase = baseData.at(-1) ?? 0;
  const lastRl   = rlData.at(-1)   ?? 0;
  const delta    = lastBase > 0 ? ((lastRl - lastBase) / lastBase) * 100 : 0;
  const rlWins   = higherIsBetter ? lastRl > lastBase : lastRl < lastBase;

  return (
    <div className="lc-wrap">
      <div className="lc-head">
        <span className="lc-title">{title}</span>
        <div className="lc-legend">
          <div className="lc-dot" style={{ background:"#1d4ed8" }} />
          <span className="lc-num" style={{ color:"#1d4ed8" }}>{lastBase.toFixed(2)}</span>
          <div className="lc-dot" style={{ background:"#15803d" }} />
          <span className="lc-num" style={{ color:"#15803d" }}>{lastRl.toFixed(2)}</span>
          {baseData.length > 1 && (
            <span className={`lc-badge ${rlWins?"win":"lose"}`}>
              {rlWins?(higherIsBetter?"▲":"▼"):(higherIsBetter?"▼":"▲")}{" "}
              {Math.abs(delta).toFixed(1)}%
            </span>
          )}
        </div>
        <span className="lc-unit">{unit}</span>
      </div>
      <div className="lc-canvas" style={{ height }}>
        <canvas ref={canvasRef} />
      </div>
      <style>{`
        .lc-wrap { background:#fff; border:1px solid #e2ddd5; border-radius:6px; display:flex; flex-direction:column; overflow:hidden; }
        .lc-head { display:flex; align-items:center; gap:8px; padding:8px 14px; border-bottom:1px solid #e2ddd5; background:#fafaf7; flex-wrap:wrap; }
        .lc-title { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; letter-spacing:0.14em; color:#71717a; flex:1; }
        .lc-legend { display:flex; align-items:center; gap:5px; }
        .lc-dot { width:8px; height:8px; border-radius:50%; }
        .lc-num { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; }
        .lc-badge { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; padding:2px 6px; border-radius:3px; }
        .lc-badge.win  { color:#15803d; background:#dcfce7; }
        .lc-badge.lose { color:#b91c1c; background:#fef2f2; }
        .lc-unit { font-family:'JetBrains Mono',monospace; font-size:8px; color:#a1a1aa; }
        .lc-canvas { padding:10px 8px 6px 12px; }
        .lc-canvas canvas { width:100% !important; height:100% !important; }
      `}</style>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function MetricsComparison() {
  const { metricsHistory: h, isRunning } = useTrafficStore();

  return (
    <div className="mc">
      {/* Toolbar — NO CSV button here, it lives in SessionRecorder at bottom of left panel */}
      <div className="mc-toolbar">
        <div className="mc-legend">
          <div className="mc-dot" style={{ background:"#1d4ed8" }} />
          <span className="mc-lbl" style={{ color:"#1d4ed8" }}>Baseline</span>
          <div className="mc-dot" style={{ background:"#15803d" }} />
          <span className="mc-lbl" style={{ color:"#15803d" }}>RL Agent</span>
        </div>
        {isRunning && (
          <div className="mc-live">
            <div className="mc-live-dot" />
            <span>LIVE</span>
          </div>
        )}
      </div>

      {/* 2-column chart grid */}
      <div className="mc-grid">
        <div className="mc-full"><WaitingTimeChart /></div>
        <div className="mc-half">
          <LineChart title="AVG SPEED"    baseData={h.baseline.avg_speed}  rlData={h.rl.avg_speed}  unit="m/s" higherIsBetter={true}  height={110} />
        </div>
        <div className="mc-half"><QueueLengthChart /></div>
        <div className="mc-full">
          <LineChart title="THROUGHPUT"   baseData={h.baseline.throughput} rlData={h.rl.throughput} unit="veh" higherIsBetter={true}  height={110} />
        </div>
      </div>

      <style>{`
        .mc { display:flex; flex-direction:column; height:100%; background:#f7f6f1; }

        .mc-toolbar {
          display:flex; align-items:center; gap:10px;
          padding:8px 14px;
          background:#fff; border-bottom:1px solid #e2ddd5;
          flex-shrink:0;
        }
        .mc-legend { display:flex; align-items:center; gap:6px; flex:1; }
        .mc-dot { width:9px; height:9px; border-radius:50%; }
        .mc-lbl { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; margin-right:4px; }

        /* EASTER EGG: live dot = traffic green */
        .mc-live {
          display:flex; align-items:center; gap:5px;
          font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700;
          color:#16a34a; letter-spacing:0.12em;
        }
        .mc-live-dot {
          width:7px; height:7px; border-radius:50%;
          background:#16a34a; box-shadow:0 0 8px rgba(22,163,74,0.4);
          animation:signal-pulse 1.5s ease-in-out infinite;
        }

        .mc-grid {
          flex:1; overflow-y:auto;
          display:grid; grid-template-columns:1fr 1fr;
          gap:10px; padding:12px;
          align-content:start;
        }
        .mc-full { grid-column:1 / -1; }
        .mc-half { grid-column:span 1; }
      `}</style>
    </div>
  );
}