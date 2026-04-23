import { useTrafficStore } from "../../store/TrafficStore";

export default function PerformanceBadge() {
  const { metricsHistory } = useTrafficStore();

  const latestWait = metricsHistory.rl.avg_waiting_time.at(-1) || 0;

  let status = "EXCELLENT";
  let color = "#00e676";

  if (latestWait > 15) {
    status = "POOR";
    color = "#ff3255";
  } else if (latestWait > 8) {
    status = "GOOD";
    color = "#ffc107";
  }

  return (
    <div
      className="perf-badge"
      style={{ borderColor: `${color}40`, background: `${color}20` }}
    >
      <span className="perf-label" style={{ color }}>
        {status}
      </span>
      <style>{`
        .perf-badge {
          display: flex;
          align-items: center;
          padding: 0.15rem 0.5rem;
          border: 1px solid;
          flex-shrink: 0;
        }
        .perf-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.55rem;
          font-weight: 800;
          letter-spacing: 0.1em;
        }
      `}</style>
    </div>
  );
}