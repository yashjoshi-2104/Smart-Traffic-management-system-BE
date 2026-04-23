// components/ParallelView/SimulationCanvas.tsx
import { useEffect, useRef, useMemo } from "react";
import type { SimulationState, TrafficLightState } from "../../types";

interface Props {
  state: SimulationState | null;
  accent: string;
  networkType?: string;
}

const W = 400;
const H = 400;

const VEHICLE_COLORS: Record<string, string> = {
  passenger:  "#4fc3f7",
  truck:      "#ff8a65",
  motorcycle: "#ce93d8",
  bus:        "#a5d6a7",
  emergency:  "#ff3255",
  default:    "#90caf9",
};

function signalColor(ch: string): string {
  if (ch === "G" || ch === "g") return "#00e676";
  if (ch === "y" || ch === "Y") return "#ffaa00";
  return "#ff3255";
}

function getSignals(tl: TrafficLightState | undefined): { ns: string; ew: string } {
  if (typeof tl?.state === 'number') {
    const phase = tl.state;
    switch (phase) {
      case 0: return { ns: "#00e676", ew: "#ff3255" };
      case 1: return { ns: "#ffaa00", ew: "#ff3255" };
      case 2: return { ns: "#ff3255", ew: "#00e676" };
      case 3: return { ns: "#ff3255", ew: "#ffaa00" };
      default: return { ns: "#444444", ew: "#444444" };
    }
  }
  
  if (!tl?.state) return { ns: "#444444", ew: "#444444" };
  return {
    ns: signalColor(tl.state[0] ?? "r"),
    ew: signalColor(tl.state[4] ?? tl.state[2] ?? "r"),
  };
}

function calculateViewport(vehicles: any[], networkType?: string) {
  const isComplexNetwork = networkType === 'complex_grid_3x3';
  
  if (isComplexNetwork) {
    return {
      minX: -50,
      maxX: 650,
      minY: -50,
      maxY: 650,
      isComplex: true
    };
  }

  if (vehicles.length === 0) {
    return { minX: 0, maxX: 200, minY: 0, maxY: 200, isComplex: false };
  }

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  vehicles.forEach(v => {
    minX = Math.min(minX, v.x);
    maxX = Math.max(maxX, v.x);
    minY = Math.min(minY, v.y);
    maxY = Math.max(maxY, v.y);
  });

  const rangeX = maxX - minX;
  const rangeY = maxY - minY;
  
  const isComplex = rangeX > 400 || rangeY > 400 || maxX > 400 || maxY > 400;

  if (isComplex) {
    return {
      minX: -50,
      maxX: 650,
      minY: -50,
      maxY: 650,
      isComplex: true
    };
  }

  const paddingX = Math.max(rangeX * 0.2, 50);
  const paddingY = Math.max(rangeY * 0.2, 50);

  return {
    minX: minX - paddingX,
    maxX: maxX + paddingX,
    minY: minY - paddingY,
    maxY: maxY + paddingY,
    isComplex: false
  };
}

function sumoToCanvas(
  sumoX: number, 
  sumoY: number, 
  viewport: any
): [number, number] {
  const rangeX = viewport.maxX - viewport.minX;
  const rangeY = viewport.maxY - viewport.minY;
  
  const canvasX = ((sumoX - viewport.minX) / rangeX) * W;
  const canvasY = H - ((sumoY - viewport.minY) / rangeY) * H;
  
  return [canvasX, canvasY];
}

function drawSimpleIntersection(
  ctx: CanvasRenderingContext2D,
  viewport: any
) {
  const CX = W / 2;
  const CY = H / 2;
  const ROAD_W = 50;
  const BOX = 60;

  ctx.fillStyle = "#1a1d25";
  ctx.fillRect(0, CY - ROAD_W, W, ROAD_W * 2);
  ctx.fillRect(CX - ROAD_W, 0, ROAD_W * 2, H);

  ctx.fillStyle = "#2a2e38";
  ctx.fillRect(0, CY - ROAD_W + 5, W, ROAD_W * 2 - 10);
  ctx.fillRect(CX - ROAD_W + 5, 0, ROAD_W * 2 - 10, H);

  ctx.fillStyle = "#353945";
  ctx.fillRect(CX - BOX, CY - BOX, BOX * 2, BOX * 2);

  ctx.setLineDash([15, 10]);
  ctx.strokeStyle = "#ffc107";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, CY); ctx.lineTo(CX - BOX, CY);
  ctx.moveTo(CX + BOX, CY); ctx.lineTo(W, CY);
  ctx.moveTo(CX, 0); ctx.lineTo(CX, CY - BOX);
  ctx.moveTo(CX, CY + BOX); ctx.lineTo(CX, H);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 3;
  [
    [0, CY - ROAD_W, W, CY - ROAD_W],
    [0, CY + ROAD_W, W, CY + ROAD_W],
    [CX - ROAD_W, 0, CX - ROAD_W, H],
    [CX + ROAD_W, 0, CX + ROAD_W, H],
  ].forEach(([x1, y1, x2, y2]) => {
    ctx.beginPath(); 
    ctx.moveTo(x1, y1); 
    ctx.lineTo(x2, y2); 
    ctx.stroke();
  });

  const tlSize = 8;
  const tlOffset = BOX + 15;
  ctx.fillStyle = "#1a1d25";
  ctx.strokeStyle = "#ffaa00";
  ctx.lineWidth = 1;
  [
    [CX, CY - tlOffset],
    [CX, CY + tlOffset],
    [CX - tlOffset, CY],
    [CX + tlOffset, CY],
  ].forEach(([x, y]) => {
    ctx.fillRect(x - tlSize/2, y - tlSize/2, tlSize, tlSize);
    ctx.strokeRect(x - tlSize/2, y - tlSize/2, tlSize, tlSize);
  });
}

function drawComplexGrid(
  ctx: CanvasRenderingContext2D,
  viewport: any
) {
  // Junction positions from SUMO
  const junctions = [1.6, 301.6, 601.6];
  const roadWidth = 50; // WIDER to catch all vehicles
  
  // Draw the ENTIRE grid as one continuous road network
  // Horizontal roads (3 rows spanning full width)
  ctx.fillStyle = "#2a2e38";
  junctions.forEach(y => {
    const [x1, y1] = sumoToCanvas(0, y, viewport);
    const [x2, y2] = sumoToCanvas(650, y, viewport);
    // Draw full-width road
    ctx.fillRect(0, y1 - roadWidth, W, roadWidth * 2);
  });
  
  // Vertical roads (3 columns spanning full height)
  junctions.forEach(x => {
    const [x1, y1] = sumoToCanvas(x, 0, viewport);
    const [x2, y2] = sumoToCanvas(x, 650, viewport);
    // Draw full-height road
    ctx.fillRect(x1 - roadWidth, 0, roadWidth * 2, H);
  });
  
  // White road edges
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 4;
  
  // Horizontal road edges
  junctions.forEach(y => {
    const [x1, y1] = sumoToCanvas(0, y, viewport);
    // Top edge
    ctx.beginPath();
    ctx.moveTo(0, y1 - roadWidth);
    ctx.lineTo(W, y1 - roadWidth);
    ctx.stroke();
    // Bottom edge
    ctx.beginPath();
    ctx.moveTo(0, y1 + roadWidth);
    ctx.lineTo(W, y1 + roadWidth);
    ctx.stroke();
  });
  
  // Vertical road edges
  junctions.forEach(x => {
    const [x1, y1] = sumoToCanvas(x, 0, viewport);
    // Left edge
    ctx.beginPath();
    ctx.moveTo(x1 - roadWidth, 0);
    ctx.lineTo(x1 - roadWidth, H);
    ctx.stroke();
    // Right edge
    ctx.beginPath();
    ctx.moveTo(x1 + roadWidth, 0);
    ctx.lineTo(x1 + roadWidth, H);
    ctx.stroke();
  });
  
  // Yellow lane dividers
  ctx.setLineDash([15, 10]);
  ctx.strokeStyle = "#ffc107";
  ctx.lineWidth = 3;
  
  // Horizontal lane dividers
  junctions.forEach(y => {
    const [x1, y1] = sumoToCanvas(0, y, viewport);
    ctx.beginPath();
    ctx.moveTo(0, y1);
    ctx.lineTo(W, y1);
    ctx.stroke();
  });
  
  // Vertical lane dividers
  junctions.forEach(x => {
    const [x1, y1] = sumoToCanvas(x, 0, viewport);
    ctx.beginPath();
    ctx.moveTo(x1, 0);
    ctx.lineTo(x1, H);
    ctx.stroke();
  });
  
  ctx.setLineDash([]);
  
  // Intersection boxes with labels
  const labels = ['C', 'B', 'A']; // Row labels (top to bottom)
  junctions.forEach((x, colIndex) => {
    junctions.forEach((y, rowIndex) => {
      const [cx, cy] = sumoToCanvas(x, y, viewport);
      const boxSize = 40;
      
      // Dark intersection box
      ctx.fillStyle = "#353945";
      ctx.fillRect(cx - boxSize/2, cy - boxSize/2, boxSize, boxSize);
      
      // Yellow border
      ctx.strokeStyle = "#ffaa00";
      ctx.lineWidth = 2;
      ctx.strokeRect(cx - boxSize/2, cy - boxSize/2, boxSize, boxSize);
      
      // Center dot
      ctx.fillStyle = "#ffaa00";
      ctx.beginPath();
      ctx.arc(cx, cy, 5, 0, Math.PI * 2);
      ctx.fill();
      
      // Grid label (A0, A1, A2, B0, B1, B2, C0, C1, C2)
      ctx.fillStyle = "#ffaa00";
      ctx.font = '700 11px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const label = `${labels[rowIndex]}${colIndex}`;
      ctx.fillText(label, cx, cy - boxSize/2 - 14);
    });
  });
  
  // Reset text alignment
  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';
}
function drawScene(
  ctx: CanvasRenderingContext2D,
  state: SimulationState | null,
  viewport: any
) {
  ctx.fillStyle = "#0e1015";
  ctx.fillRect(0, 0, W, H);

  if (viewport.isComplex) {
    // Grid background
    ctx.strokeStyle = "#14161d";
    ctx.lineWidth = 0.5;
    const gridSize = 40;
    for (let x = 0; x < W; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y < H; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }
    
    // PASS VEHICLES to help detect road positions
    drawComplexGrid(ctx, viewport, state?.vehicles || []);
  } else {
    drawSimpleIntersection(ctx, viewport);
  }

  if (!state?.vehicles?.length) return;

  // Draw vehicles
  state.vehicles.forEach((v) => {
    const [cx, cy] = sumoToCanvas(v.x, v.y, viewport);
    
    if (cx < -10 || cx > W + 10 || cy < -10 || cy > H + 10) return;

    const isEmergency = v.type === "emergency" || v.is_emergency;
    const color = isEmergency ? VEHICLE_COLORS.emergency : (VEHICLE_COLORS[v.type] ?? VEHICLE_COLORS.default);
    const alpha = Math.round((0.5 + Math.min(v.speed / 15, 1) * 0.5) * 255)
      .toString(16).padStart(2, "0");

    // Emergency pulse
    if (isEmergency) {
      const pulseRadius = 8 + Math.sin(Date.now() / 200) * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, pulseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = color + "44";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Vehicle dot
    ctx.beginPath();
    ctx.arc(cx, cy, isEmergency ? 4.5 : 3.5, 0, Math.PI * 2);
    ctx.fillStyle = color + alpha;
    ctx.fill();

    // Speed ring
    if (v.speed > 0.5) {
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.strokeStyle = color + "2a";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });

  // HUD
  const emergencyCount = state.vehicles.filter(v => v.is_emergency || v.type === "emergency").length;
  const networkType = viewport.isComplex ? "COMPLEX" : "SIMPLE";
  
  ctx.fillStyle = "rgba(0,0,0,0.65)";
  ctx.fillRect(7, 7, 140, 16);
  ctx.fillStyle = "#4a5060";
  ctx.font = `700 9px 'JetBrains Mono', monospace`;
  ctx.fillText(`${networkType} • STEP ${state.step}`, 12, 18);
  
  if (emergencyCount > 0) {
    ctx.fillStyle = "#ff3255";
    ctx.fillText(`🚨 ${emergencyCount}`, 110, 18);
  }
}

export default function SimulationCanvas({ state, accent, networkType }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const viewport = useMemo(() => {
    if (!state?.vehicles) return { minX: 0, maxX: 200, minY: 0, maxY: 200, isComplex: false };
    return calculateViewport(state.vehicles, networkType);
  }, [state?.vehicles, networkType]);
 
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    drawScene(ctx, state, viewport);
  }, [state, viewport]);

  const tl = state?.traffic_lights?.[0];
  const { ns, ew } = getSignals(tl);
  const emergencyCount = state?.vehicles?.filter(v => v.is_emergency || v.type === "emergency").length ?? 0;

  return (
    <div className="sim-canvas-wrap">
      <canvas ref={canvasRef} width={W} height={H} />

      {!state && (
        <div className="idle-overlay">
          <div className="idle-ring" style={{ borderColor: accent + "33" }} />
          <span className="idle-label">AWAITING SIM</span>
        </div>
      )}

      <div className="signal-strip">
        <span className="sig-item">
          <span className="sig-dot" style={{ background: ns, boxShadow: `0 0 6px ${ns}` }} />
          N/S
        </span>
        <span className="sig-divider">|</span>
        <span className="sig-item">
          <span className="sig-dot" style={{ background: ew, boxShadow: `0 0 6px ${ew}` }} />
          E/W
        </span>
        <span className="sig-spacer" />
        {emergencyCount > 0 && (
          <span className="sig-emergency">🚨 {emergencyCount}</span>
        )}
        <span className="sig-vcount">{state?.vehicles.length ?? 0} veh</span>
      </div>

      <style>{`
        .sim-canvas-wrap {
          position: relative;
          background: #0e1015;
          line-height: 0;
        }
        .sim-canvas-wrap canvas { width: 100%; height: auto; display: block; }

        .idle-overlay {
          position: absolute; inset: 0;
          display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          gap: 0.75rem;
          background: rgba(14,16,21,0.88);
        }
        .idle-ring {
          width: 48px; height: 48px; border-radius: 50%;
          border: 2px solid;
          animation: spin 3s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .idle-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.6rem; letter-spacing: 0.2em;
          color: #3a3f4d; font-weight: 700;
        }

        .signal-strip {
          display: flex; align-items: center; gap: 0.5rem;
          padding: 0.3rem 0.6rem;
          background: #12141a;
          border-top: 1px solid #1e2128;
        }
        .sig-item {
          display: flex; align-items: center; gap: 0.35rem;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; color: #5a6070; font-weight: 700;
          letter-spacing: 0.08em;
        }
        .sig-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; transition: background 0.3s; }
        .sig-divider { color: #2e3240; font-size: 0.7rem; }
        .sig-spacer { flex: 1; }
        .sig-emergency {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; color: #ff3255; font-weight: 800;
          animation: blink 1s ease-in-out infinite;
        }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
        .sig-vcount {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem; color: #3a3f4d;
        }
      `}</style>
    </div>
  );
}