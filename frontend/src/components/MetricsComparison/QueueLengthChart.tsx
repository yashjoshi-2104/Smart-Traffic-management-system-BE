// components/MetricsComparison/QueueLengthChart.tsx
import { useEffect, useRef } from "react";
import {
  Chart, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, Filler, Tooltip,
} from "chart.js";
import { useTrafficStore } from "../../store/TrafficStore";

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip);

const BASE_COLOR = "#1d4ed8";
const RL_COLOR   = "#15803d";

function getQueueColor(queue: number): string {
  if (queue <= 3)  return "#16a34a";
  if (queue <= 8)  return "#f59e0b";
  return "#dc2626";
}

export default function QueueLengthChart() {
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
          { label:"Baseline", data:[], borderColor:BASE_COLOR, backgroundColor:"rgba(29,78,216,0.06)", borderWidth:1.5, pointRadius:0, fill:true, tension:0.4 },
          { label:"RL Agent", data:[], borderColor:RL_COLOR,   backgroundColor:"rgba(21,128,61,0.06)",  borderWidth:1.5, pointRadius:0, fill:true, tension:0.4 },
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
            callbacks:{ label:(i) => ` ${i.dataset.label}: ${(i.raw as number).toFixed(1)} veh` },
          },
        },
        scales:{
          x:{ display:false },
          y:{
            position:"right",
            grid:{ color:"#f2f1ec", lineWidth:1 },
            border:{ color:"#e2ddd5" },
            ticks:{ color:"#a1a1aa", font:{ family:"'JetBrains Mono',monospace", size:9 }, maxTicksLimit:4, callback:(v) => `${v}` },
          },
        },
      },
    });
    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.data.labels           = h.baseline.queue_length.map((_,i) => i.toString());
    chartRef.current.data.datasets[0].data = h.baseline.queue_length;
    chartRef.current.data.datasets[1].data = h.rl.queue_length;
    chartRef.current.update("none");
  }, [h]);

  const lastBase = h.baseline.queue_length.at(-1) ?? 0;
  const lastRl   = h.rl.queue_length.at(-1)       ?? 0;
  const delta    = lastBase > 0 ? ((lastRl - lastBase) / lastBase) * 100 : 0;
  const rlWins   = lastRl < lastBase;
  const baseColor = getQueueColor(lastBase);
  const rlColor   = getQueueColor(lastRl);

  return (
    <div className="qlc-wrap">
      <div className="qlc-header">
        <span className="qlc-title">QUEUE LENGTH</span>
        <div className="qlc-legend">
          <span className="qlc-dot" style={{ background: BASE_COLOR }} />
          <span className="qlc-val" style={{ color: BASE_COLOR }}>{lastBase.toFixed(1)}</span>
          <span className="qlc-dot" style={{ background: RL_COLOR }} />
          <span className="qlc-val" style={{ color: RL_COLOR }}>{lastRl.toFixed(1)}</span>
          {h.baseline.queue_length.length > 1 && (
            <span className={`qlc-delta ${rlWins ? "win" : "lose"}`}>
              {rlWins ? "▼" : "▲"} {Math.abs(delta).toFixed(1)}%
            </span>
          )}
        </div>
        <span className="qlc-unit">veh</span>
      </div>

      {/* Progress bars — traffic light colour coding */}
      <div className="qlc-bars">
        <div className="qlc-bar-row">
          <span className="qlc-bar-label">BASELINE</span>
          <div className="qlc-bar-track">
            <div className="qlc-bar-fill" style={{ width:`${Math.min((lastBase/20)*100,100)}%`, background:baseColor }} />
          </div>
          <span className="qlc-bar-val" style={{ color:baseColor }}>{lastBase.toFixed(1)}</span>
        </div>
        <div className="qlc-bar-row">
          <span className="qlc-bar-label">RL AGENT</span>
          <div className="qlc-bar-track">
            <div className="qlc-bar-fill" style={{ width:`${Math.min((lastRl/20)*100,100)}%`, background:rlColor }} />
          </div>
          <span className="qlc-bar-val" style={{ color:rlColor }}>{lastRl.toFixed(1)}</span>
        </div>
      </div>

      <div className="qlc-canvas">
        <canvas ref={canvasRef} />
      </div>

      <style>{`
        .qlc-wrap { background:#fff; border:1px solid #e2ddd5; border-radius:6px; display:flex; flex-direction:column; overflow:hidden; }
        .qlc-header { display:flex; align-items:center; gap:6px; padding:8px 14px; border-bottom:1px solid #e2ddd5; background:#fafaf7; flex-wrap:wrap; }
        .qlc-title { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; letter-spacing:0.14em; color:#71717a; flex:1; }
        .qlc-legend { display:flex; align-items:center; gap:5px; }
        .qlc-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
        .qlc-val { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; }
        .qlc-delta { font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; padding:2px 6px; border-radius:3px; }
        .qlc-delta.win  { color:#15803d; background:#dcfce7; }
        .qlc-delta.lose { color:#b91c1c; background:#fef2f2; }
        .qlc-unit { font-family:'JetBrains Mono',monospace; font-size:8px; color:#a1a1aa; }
        .qlc-bars { padding:10px 14px; background:#fafaf7; border-bottom:1px solid #e2ddd5; display:flex; flex-direction:column; gap:7px; }
        .qlc-bar-row { display:grid; grid-template-columns:62px 1fr 38px; align-items:center; gap:8px; }
        .qlc-bar-label { font-family:'JetBrains Mono',monospace; font-size:8px; font-weight:700; color:#71717a; letter-spacing:0.06em; }
        .qlc-bar-track { height:14px; background:#f2f1ec; border:1px solid #e2ddd5; border-radius:2px; overflow:hidden; }
        .qlc-bar-fill { height:100%; transition:width 0.4s ease, background 0.3s ease; border-radius:2px; }
        .qlc-bar-val { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:800; text-align:right; }
        .qlc-canvas { height:90px; padding:8px 8px 6px 12px; }
        .qlc-canvas canvas { width:100% !important; height:100% !important; }
      `}</style>
    </div>
  );
}