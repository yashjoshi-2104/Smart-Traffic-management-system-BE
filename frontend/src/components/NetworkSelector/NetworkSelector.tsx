// components/NetworkSelector/NetworkSelector.tsx
import React, { useState, useEffect } from "react";

interface Network {
  id: string;
  name: string;
  description: string;
  intersections: number;
  complexity: string;
}

interface Props {
  disabled?: boolean;
}

const ALLOWED_NETWORKS = ["simple_intersection", "urban_arterial"];

const NETWORK_META: Record<string, { label: string; tag: string; desc: string; tls: string }> = {
  simple_intersection: {
    label: "Simple",
    tag:   "1 TLS",
    desc:  "Single 4-way intersection",
    tls:   "center",
  },
  urban_arterial: {
    label: "Urban Arterial",
    tag:   "5 TLS",
    desc:  "3×3 grid arterial",
    tls:   "B1",
  },
};

export const NetworkSelector: React.FC<Props> = ({ disabled = false }) => {
  const [current, setCurrent]   = useState<string>("simple_intersection");
  const [loading, setLoading]   = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/simulation/networks")
      .then(r => r.json())
      .then(d => { if (d.current) setCurrent(d.current); })
      .catch(() => {});
  }, []);

  const select = async (id: string) => {
    if (id === current || disabled || loading) return;
    setLoading(id);
    try {
      const r = await fetch("http://localhost:8000/api/simulation/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ network: id }),
      });
      if (r.ok) setCurrent(id);
    } catch {}
    finally { setLoading(null); }
  };

  return (
    <div className="ns-wrap">
      <span className="ns-label">NETWORK</span>
      <div className="ns-buttons">
        {ALLOWED_NETWORKS.map(id => {
          const meta   = NETWORK_META[id];
          const active = current === id;
          const busy   = loading === id;
          return (
            <button
              key={id}
              className={`ns-btn ${active ? "ns-active" : ""}`}
              onClick={() => select(id)}
              disabled={disabled || !!loading}
            >
              <div className="ns-btn-top">
                {/* Active dot */}
                <div className="ns-btn-dot" style={{
                  background: active ? "#1d4ed8" : "#e2ddd5",
                  boxShadow:  active ? "0 0 6px rgba(29,78,216,0.4)" : "none",
                }} />
                <span className="ns-btn-label" style={{ color: active ? "#1d4ed8" : "#3f3f46" }}>
                  {busy ? "Switching…" : meta.label}
                </span>
                <span className="ns-btn-tag" style={{
                  color:      active ? "#1d4ed8" : "#a1a1aa",
                  background: active ? "#eff6ff" : "#f2f1ec",
                  borderColor: active ? "#dbeafe" : "#e2ddd5",
                }}>{meta.tag}</span>
              </div>
              <span className="ns-btn-desc">{meta.desc}</span>
            </button>
          );
        })}
      </div>

      <style>{`
        .ns-wrap { display:flex; flex-direction:column; gap:6px; }
        .ns-label {
          font-family:'JetBrains Mono',monospace;
          font-size:8px; font-weight:700; letter-spacing:0.16em; color:#71717a;
        }
        .ns-buttons { display:flex; flex-direction:column; gap:5px; }
        .ns-btn {
          background:#fff;
          border:1px solid #e2ddd5;
          padding:10px 12px;
          border-radius:6px;
          cursor:pointer;
          display:flex; flex-direction:column; gap:3px;
          text-align:left;
          transition:all 0.15s;
          width:100%;
        }
        .ns-btn:hover:not(:disabled):not(.ns-active) {
          border-color:#c8c3ba;
          background:#fafaf7;
        }
        .ns-btn:disabled { opacity:0.4; cursor:not-allowed; }
        .ns-btn.ns-active {
          border-color:#1d4ed860;
          background:#eff6ff;
        }
        .ns-btn-top {
          display:flex; align-items:center; gap:6px;
        }
        .ns-btn-dot {
          width:7px; height:7px; border-radius:50%; flex-shrink:0;
          transition:all 0.2s;
        }
        .ns-btn-label {
          font-family:'JetBrains Mono',monospace;
          font-size:11px; font-weight:700; flex:1;
          transition:color 0.15s;
        }
        .ns-btn-tag {
          font-family:'JetBrains Mono',monospace;
          font-size:8px; font-weight:700; letter-spacing:0.08em;
          padding:2px 6px; border:1px solid; border-radius:3px;
        }
        .ns-btn-desc {
          font-family:'JetBrains Mono',monospace;
          font-size:9px; color:#a1a1aa;
          padding-left:13px;
        }
        .ns-btn.ns-active .ns-btn-desc { color:#71717a; }
      `}</style>
    </div>
  );
};