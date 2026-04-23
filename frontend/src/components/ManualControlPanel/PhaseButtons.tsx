// src/components/ManualControlPanel/PhaseButtons.tsx
import { useState } from "react";
import { controlAPI } from "../../services/apiClient";

interface Props {
  trafficLightId: string;
  onError?: (msg: string) => void;
}

export default function PhaseButtons({ trafficLightId, onError }: Props) {
  const [isChanging, setIsChanging] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<number | null>(null);

  const handlePhaseChange = async (phase: number, label: string) => {
    setIsChanging(true);
    try {
      console.log(`🔄 Changing to phase ${phase}: ${label} for TLS: ${trafficLightId}`);
      await controlAPI.setPhase(trafficLightId, phase);
      setCurrentPhase(phase);
      console.log(`✅ Changed to phase ${phase}: ${label}`);
    } catch (error) {
      console.error("❌ Failed to change phase:", error);
      const errorMsg = error instanceof Error ? error.message : "Failed to change signal phase";
      onError?.(errorMsg);
    } finally {
      setIsChanging(false);
    }
  };

  const phases = [
    { phase: 0, label: "N/S Green", icon: "↑↓", color: "#00e676" },
    { phase: 2, label: "E/W Green", icon: "←→", color: "#00e676" },
    { phase: 1, label: "N/S Yellow", icon: "↑↓", color: "#ffaa00" },
    { phase: 3, label: "E/W Yellow", icon: "←→", color: "#ffaa00" },
  ];

  return (
    <div className="phase-buttons">
      <div className="phase-grid">
        {phases.map(({ phase, label, icon, color }) => (
          <button
            key={phase}
            onClick={() => handlePhaseChange(phase, label)}
            disabled={isChanging}
            className={`phase-btn ${currentPhase === phase ? "active" : ""}`}
            style={{
              "--phase-color": color,
            } as React.CSSProperties}
          >
            <span className="phase-icon">{icon}</span>
            <span className="phase-label">{label}</span>
          </button>
        ))}
      </div>

      <style>{`
        .phase-buttons {
          padding: 0.85rem;
          flex: 1;
          overflow-y: auto;
        }

        .phase-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 0.5rem;
        }

        .phase-btn {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.4rem;
          padding: 0.75rem 0.5rem;
          background: #1a1d25;
          border: 1px solid #2e3240;
          color: #8a92a8;
          font-family: 'JetBrains Mono', monospace;
          cursor: pointer;
          transition: all 0.2s;
        }

        .phase-btn:hover:not(:disabled) {
          background: #22252e;
          border-color: var(--phase-color);
          color: #c5cad8;
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        .phase-btn.active {
          background: #22252e;
          border-color: var(--phase-color);
          box-shadow: 0 0 10px var(--phase-color)33;
          color: var(--phase-color);
        }

        .phase-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .phase-icon {
          font-size: 1.3rem;
          line-height: 1;
        }

        .phase-label {
          font-size: 0.62rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }
      `}</style>
    </div>
  );
}