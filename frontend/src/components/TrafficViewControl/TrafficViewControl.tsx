// frontend/src/components/TrafficViewControl/TrafficViewControl.tsx
import { useState } from 'react';

interface TrafficViewControlProps {
  disabled?: boolean;
}

export default function TrafficViewControl({ disabled = false }: TrafficViewControlProps) {
  const [baselineEnabled, setBaselineEnabled] = useState(false);
  const [rlEnabled, setRlEnabled] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleToggle = async (type: 'baseline' | 'rl', enabled: boolean) => {
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/simulation/gui/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseline: type === 'baseline' ? enabled : baselineEnabled,
          rl: type === 'rl' ? enabled : rlEnabled
        })
      });

      if (response.ok) {
        if (type === 'baseline') setBaselineEnabled(enabled);
        if (type === 'rl') setRlEnabled(enabled);
      }
    } catch (error) {
      console.error('Failed to toggle GUI:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="traffic-view-control">
      <div className="tvc-header">
        <span className="tvc-icon">👁️</span>
        <span className="tvc-title">TRAFFIC VISUALIZATION</span>
      </div>

      <div className="tvc-options">
        <div className="tvc-option">
          <label className="tvc-toggle">
            <input
              type="checkbox"
              checked={baselineEnabled}
              onChange={(e) => handleToggle('baseline', e.target.checked)}
              disabled={disabled || loading}
            />
            <span className="tvc-toggle-slider"></span>
          </label>
          <div className="tvc-option-info">
            <span className="tvc-option-label">Baseline Traffic View</span>
            <span className="tvc-option-desc">Opens SUMO GUI for baseline simulation</span>
          </div>
          <div className={`tvc-badge ${baselineEnabled ? 'active' : ''}`}>
            {baselineEnabled ? '● ENABLED' : '○ DISABLED'}
          </div>
        </div>

        <div className="tvc-option">
          <label className="tvc-toggle">
            <input
              type="checkbox"
              checked={rlEnabled}
              onChange={(e) => handleToggle('rl', e.target.checked)}
              disabled={disabled || loading}
            />
            <span className="tvc-toggle-slider"></span>
          </label>
          <div className="tvc-option-info">
            <span className="tvc-option-label">RL Agent Traffic View</span>
            <span className="tvc-option-desc">Opens SUMO GUI for RL simulation</span>
          </div>
          <div className={`tvc-badge ${rlEnabled ? 'active' : ''}`}>
            {rlEnabled ? '● ENABLED' : '○ DISABLED'}
          </div>
        </div>
      </div>

      {(baselineEnabled || rlEnabled) && (
        <div className="tvc-notice">
          <span className="tvc-notice-icon">ℹ️</span>
          <span className="tvc-notice-text">
            Restart simulation to open SUMO windows
          </span>
        </div>
      )}

      <style>{`
        .traffic-view-control {
          background: #12141a;
          border: 1px solid #1e2128;
          display: flex;
          flex-direction: column;
        }

        .tvc-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.6rem 0.75rem;
          border-bottom: 1px solid #1e2128;
          background: #0e1015;
        }

        .tvc-icon {
          font-size: 1rem;
        }

        .tvc-title {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.65rem;
          font-weight: 800;
          letter-spacing: 0.12em;
          color: #7a8090;
        }

        .tvc-options {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 0.75rem;
        }

        .tvc-option {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          background: #0e1015;
          border: 1px solid #1e2128;
          transition: border-color 0.2s;
        }

        .tvc-option:hover {
          border-color: #2e3240;
        }

        .tvc-toggle {
          position: relative;
          width: 44px;
          height: 24px;
          flex-shrink: 0;
          cursor: pointer;
        }

        .tvc-toggle input {
          opacity: 0;
          width: 0;
          height: 0;
        }

        .tvc-toggle-slider {
          position: absolute;
          inset: 0;
          background: #1e2128;
          border: 1px solid #2e3240;
          transition: 0.3s;
        }

        .tvc-toggle-slider:before {
          position: absolute;
          content: "";
          height: 16px;
          width: 16px;
          left: 3px;
          bottom: 3px;
          background: #4a5060;
          transition: 0.3s;
        }

        .tvc-toggle input:checked + .tvc-toggle-slider {
          background: rgba(0, 230, 118, 0.2);
          border-color: #00e676;
        }

        .tvc-toggle input:checked + .tvc-toggle-slider:before {
          transform: translateX(20px);
          background: #00e676;
        }

        .tvc-toggle input:disabled + .tvc-toggle-slider {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .tvc-option-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }

        .tvc-option-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.7rem;
          font-weight: 700;
          color: #d0d5e0;
        }

        .tvc-option-desc {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem;
          color: #5a6070;
        }

        .tvc-badge {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.55rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          color: #4a5060;
          padding: 0.2rem 0.4rem;
          background: #1a1d25;
          border: 1px solid #2e3240;
          flex-shrink: 0;
        }

        .tvc-badge.active {
          color: #00e676;
          background: rgba(0, 230, 118, 0.1);
          border-color: #00e676;
        }

        .tvc-notice {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.6rem 0.75rem;
          background: rgba(255, 170, 0, 0.1);
          border-top: 1px solid rgba(255, 170, 0, 0.3);
        }

        .tvc-notice-icon {
          font-size: 0.85rem;
        }

        .tvc-notice-text {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.62rem;
          color: #ffaa00;
        }
      `}</style>
    </div>
  );
}