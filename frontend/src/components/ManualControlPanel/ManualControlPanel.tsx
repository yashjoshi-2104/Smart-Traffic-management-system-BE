// src/components/ManualControlPanel/ManualControlPanel.tsx
import { useTrafficStore } from "../../store/TrafficStore";
import PhaseButtons from "./PhaseButtons";

interface Props {
  onError?: (msg: string) => void;
}

export default function ManualControlPanel({ onError }: Props) {
  const mode = useTrafficStore((state) => state.mode);
  const trafficLights = useTrafficStore((state) => state.trafficLights);

  // Get first traffic light (for single intersection)
  const tlsId = trafficLights[0]?.id || "center";

  return (
    <div className="manual-control-panel">
      <div className="panel-header">
        <h3>Manual Signal Control</h3>
        <div className="status-badge">
          <span className="status-dot" />
          ACTIVE
        </div>
      </div>

      <PhaseButtons trafficLightId={tlsId} onError={onError} />

      <style>{`
        .manual-control-panel {
          background: #0e1015;
          border-top: 1px solid #1e2128;
          display: flex;
          flex-direction: column;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.6rem 0.85rem;
          background: #12141a;
          border-bottom: 1px solid #1e2128;
          flex-shrink: 0;
        }

        .panel-header h3 {
          margin: 0;
          font-size: 0.72rem;
          font-weight: 700;
          color: #c5cad8;
          font-family: 'JetBrains Mono', monospace;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }

        .status-badge {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.25rem 0.5rem;
          background: #1a1d25;
          border: 1px solid #ffaa0033;
          font-size: 0.55rem;
          font-weight: 700;
          color: #ffaa00;
          font-family: 'JetBrains Mono', monospace;
          letter-spacing: 0.08em;
        }

        .status-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #ffaa00;
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}