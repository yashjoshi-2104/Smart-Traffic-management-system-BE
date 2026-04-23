// hooks/useWebSocket.ts
import { useEffect } from "react";
import { useTrafficSocket } from "../services/socketClient";
import { useTrafficStore } from "../store/TrafficStore";
import type { ConnectionStatus } from "../types";

/**
 * Main hook for WebSocket lifecycle + connection status.
 * Use in your root component (MainDashboard) only — once.
 */
export function useWebSocket() {
  useTrafficSocket(); // connects, pipes state, cleans up

  const connectionStatus = useTrafficStore((s) => s.connectionStatus);
  const isRunning        = useTrafficStore((s) => s.isRunning);
  const syncDiff         = useTrafficStore((s) => s.syncDiff);

  const isLive    = connectionStatus === "connected";
  const isStale   = connectionStatus === "disconnected" && isRunning;

  return { connectionStatus, isLive, isStale, isRunning, syncDiff };
}

/**
 * Lightweight version — just connection status, no re-render on metrics.
 * Use in header/status bar components.
 */
export function useConnectionStatus(): ConnectionStatus {
  return useTrafficStore((s) => s.connectionStatus);
}