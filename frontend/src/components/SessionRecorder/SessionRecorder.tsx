// components/SessionRecorder/SessionRecorder.tsx
import { useState } from "react";
import { useTrafficStore } from "../../store/TrafficStore";

// Traffic red for REC — completing the easter egg
const T_RED   = "#dc2626";
const T_GREEN = "#16a34a";

export default function SessionRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [savedCount,  setSavedCount]  = useState(0);
  const { metricsHistory } = useTrafficStore();

  const startRecording = () => setIsRecording(true);

  const stopRecording = () => {
    const session = {
      timestamp: Date.now(),
      duration:  metricsHistory.baseline.avg_speed.length,
      data:      JSON.parse(JSON.stringify(metricsHistory)),
    };
    const existing   = localStorage.getItem("traffic_recordings");
    const recordings = existing ? JSON.parse(existing) : [];
    recordings.push(session);
    localStorage.setItem("traffic_recordings", JSON.stringify(recordings));
    setSavedCount(recordings.length);
    setIsRecording(false);
    downloadJSON(session, `session_${session.timestamp}.json`);
  };

  const exportCSV = () => {
    const h = metricsHistory;
    const len = h.baseline.avg_waiting_time.length;
    if (len === 0) return;

    const rows = ["timestamp,baseline_avg_speed,rl_avg_speed,baseline_avg_waiting,rl_avg_waiting,baseline_queue_length,rl_queue_length,baseline_throughput,rl_throughput"];
    for (let i = 0; i < len; i++) {
      rows.push([
        i,
        h.baseline.avg_speed[i]?.toFixed(4)        ?? 0,
        h.rl.avg_speed[i]?.toFixed(4)              ?? 0,
        h.baseline.avg_waiting_time[i]?.toFixed(4) ?? 0,
        h.rl.avg_waiting_time[i]?.toFixed(4)       ?? 0,
        h.baseline.queue_length[i]?.toFixed(1)     ?? 0,
        h.rl.queue_length[i]?.toFixed(1)           ?? 0,
        h.baseline.throughput[i]?.toFixed(1)       ?? 0,
        h.rl.throughput[i]?.toFixed(1)             ?? 0,
      ].join(","));
    }

    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    downloadBlob(blob, `traffic_metrics_${Date.now()}.csv`);
  };

  const downloadJSON = (data: any, filename: string) => {
    downloadBlob(new Blob([JSON.stringify(data, null, 2)], { type:"application/json" }), filename);
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="sr-wrap">
      {/* REC button — traffic red, EASTER EGG */}
      <button
        className={`sr-rec-btn ${isRecording ? "recording" : ""}`}
        onClick={isRecording ? stopRecording : startRecording}
      >
        <span className="sr-rec-dot" />
        <span>{isRecording ? "STOP REC" : "REC"}</span>
        {savedCount > 0 && (
          <span className="sr-saved">{savedCount} saved</span>
        )}
      </button>

      {/* CSV export button — baseline blue */}
      <button className="sr-csv-btn" onClick={exportCSV}>
        <span>↓</span>
        <span>CSV</span>
      </button>

      <style>{`
        .sr-wrap {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          padding: 12px;
          border-top: 1px solid #e2ddd5;
          background: #f2f1ec;
        }

        /* REC = traffic red */
        .sr-rec-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 11px 8px;
          background: rgba(220,38,38,0.08);
          border: 2px solid ${T_RED};
          border-radius: 6px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 12px;
          font-weight: 800;
          color: ${T_RED};
          cursor: pointer;
          transition: all 0.2s;
          letter-spacing: 0.06em;
        }
        .sr-rec-btn:hover { background:rgba(220,38,38,0.14); }
        .sr-rec-btn.recording {
          background: ${T_RED};
          color: #fff;
          animation: red-pulse 1s ease-in-out infinite;
        }
        .sr-rec-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: currentColor;
          flex-shrink: 0;
        }
        .sr-saved {
          font-size: 8px;
          opacity: 0.7;
          margin-left: 2px;
        }

        /* CSV = baseline blue */
        .sr-csv-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 11px 8px;
          background: #eff6ff;
          border: 1px solid #1d4ed8;
          border-radius: 6px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 12px;
          font-weight: 800;
          color: #1d4ed8;
          cursor: pointer;
          transition: all 0.2s;
          letter-spacing: 0.06em;
        }
        .sr-csv-btn:hover { background:#dbeafe; }
      `}</style>
    </div>
  );
}