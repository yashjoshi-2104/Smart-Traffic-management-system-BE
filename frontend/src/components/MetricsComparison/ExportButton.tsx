import { useTrafficStore } from "../../store/TrafficStore";

export default function ExportButton() {
  const { metricsHistory } = useTrafficStore();

  const handleExport = () => {
    // Prepare CSV data
    const headers = [
      "timestamp",
      "baseline_avg_speed",
      "rl_avg_speed",
      "baseline_avg_waiting",
      "rl_avg_waiting",
      "baseline_queue_length",
      "rl_queue_length",
      "baseline_throughput",
      "rl_throughput",
    ];

    const rows = metricsHistory.baseline.avg_speed.map((_, i) => [
      i,
      metricsHistory.baseline.avg_speed[i] || 0,
      metricsHistory.rl.avg_speed[i] || 0,
      metricsHistory.baseline.avg_waiting_time[i] || 0,
      metricsHistory.rl.avg_waiting_time[i] || 0,
      metricsHistory.baseline.queue_length[i] || 0,
      metricsHistory.rl.queue_length[i] || 0,
      metricsHistory.baseline.throughput[i] || 0,
      metricsHistory.rl.throughput[i] || 0,
    ]);

    // Create CSV content
    const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join(
      "\n"
    );

    // Download
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `traffic_metrics_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={handleExport}
      className="export-btn"
      title="Export metrics to CSV"
    >
      ⬇ CSV
      <style>{`
        .export-btn {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.6rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          padding: 0.35rem 0.6rem;
          background: #1a1d25;
          color: #00e676;
          border: 1px solid #00e67640;
          cursor: pointer;
          transition: all 0.2s;
        }
        .export-btn:hover {
          background: #00e67620;
          border-color: #00e676;
          box-shadow: 0 0 8px rgba(0, 230, 118, 0.2);
        }
      `}</style>
    </button>
  );
}