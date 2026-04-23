// components/MetricsComparison/WaitingTimeChart.tsx
import { useEffect, useRef } from "react";
import {
  Chart, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, Filler, Tooltip,
} from "chart.js";
import { useTrafficStore } from "../../store/TrafficStore";

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip);

const BASE_COLOR = "#1d4ed8";
const RL_COLOR   = "#15803d";

export default function WaitingTimeChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef  = useRef<Chart | null>(null);
  const { metricsHistory: h } = useTrafficStore();

  useEffect(() => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;

    chartRef.current = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label:"Baseline", data:[], borderColor:BASE_COLOR, backgroundColor:"rgba(29,78,216,0.07)", borderWidth:2, pointRadius:0, fill:true, tension:0.4 },
          { label:"RL Agent", data:[], borderColor:RL_COLOR,   backgroundColor:"rgba(21,128,61,0.07)",  borderWidth:2, pointRadius:0, fill:true, tension:0.4 },
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
            callbacks:{ label:(i) => ` ${i.dataset.label}: ${(i.raw as number).toFixed(2)}s` },
          },
        },
        scales:{
          x:{ display:false },
          y:{
            position:"right",
            grid:{ color:"#f2f1ec", lineWidth:1 },
            border:{ color:"#e2ddd5" },
            ticks:{ color:"#a1a1aa", font:{ family:"'JetBrains Mono',monospace", size:9 }, maxTicksLimit:5, callback:(v) => `${v}s` },
          },
        },
      },
    });
    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.data.labels           = h.baseline.avg_waiting_time.map((_,i) => i.toString());
    chartRef.current.data.datasets[0].data = h.baseline.avg_waiting_time;
    chartRef.current.data.datasets[1].data = h.rl.avg_waiting_time;
    chartRef.current.update("none");
  }, [h]);

  const lastBase = h.baseline.avg_waiting_time.at(-1) ?? 0;
  const lastRl   = h.rl.avg_waiting_time.at(-1)       ?? 0;
  const delta    = lastBase > 0 ? ((lastRl - lastBase) / lastBase) * 100 : 0;
  const rlWins   = lastRl < lastBase;

  return (
    <div className="wtc-wrap">
      <div className="wtc-header">
        <span className="wtc-title">WAIT TIME</span>
        <div className="wtc-legend">
          <div className="wtc-dot" style={{ background: BASE_COLOR }} />
          <span className="wtc-num" style={{ color: BASE_COLOR }}>{lastBase.toFixed(2)}s</span>
          <div className="wtc-dot" style={{ background: RL_COLOR }} />
          <span className="wtc-num" style={{ color: RL_COLOR }}>{lastRl.toFixed(2)}s</span>
          {h.baseline.avg_waiting_time.length > 1 && (
            <span className={`wtc-badge ${rlWins ? "win" : "lose"}`}>
              {rlWins ? "▼" : "▲"} {Math.abs(delta).toFixed(1)}%
            </span>
          )}
        </div>
        <span className="wtc-unit">seconds</span>
      </div>
      <div className="wtc-canvas">
        <canvas ref={canvasRef} />
      </div>
      <style>{`
        .wtc-wrap { background:#fff; border:1px solid #e2ddd5; border-radius:6px; display:flex; flex-direction:column; overflow:hidden; }
        .wtc-header { display:flex; align-items:center; gap:8px; padding:8px 14px; border-bottom:1px solid #e2ddd5; background:#fafaf7; flex-wrap:wrap; }
        .wtc-title { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; letter-spacing:0.14em; color:#71717a; flex:1; }
        .wtc-legend { display:flex; align-items:center; gap:5px; }
        .wtc-dot { width:8px; height:8px; border-radius:50%; }
        .wtc-num { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; }
        .wtc-badge { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; padding:2px 6px; border-radius:3px; }
        .wtc-badge.win  { color:#15803d; background:#dcfce7; }
        .wtc-badge.lose { color:#b91c1c; background:#fef2f2; }
        .wtc-unit { font-family:'JetBrains Mono',monospace; font-size:8px; color:#a1a1aa; }
        .wtc-canvas { height:130px; padding:10px 8px 6px 12px; }
        .wtc-canvas canvas { width:100% !important; height:100% !important; }
      `}</style>
    </div>
  );
}