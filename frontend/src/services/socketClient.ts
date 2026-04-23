// services/socketClient.ts
import { useEffect } from "react";
import trafficWS from "./websocket";
import { useTrafficStore } from "../store/TrafficStore";

/**
 * Drop this hook into your top-level component (MainDashboard / App).
 * It connects the WS, pipes messages into Zustand, and cleans up on unmount.
 */
export function useTrafficSocket() {
  const { applyDualState, setConnectionStatus } = useTrafficStore();

  useEffect(() => {
    const unsubMsg    = trafficWS.onMessage((state) => applyDualState(state));
    const unsubStatus = trafficWS.onStatusChange((s) => setConnectionStatus(s));

    trafficWS.connect();

    return () => {
      unsubMsg();
      unsubStatus();
      trafficWS.disconnect();
    };
  }, [applyDualState, setConnectionStatus]);
}

/**
 * Convenience: imperatively connect/disconnect from non-hook contexts.
 */
export const connectSocket    = () => trafficWS.connect();
export const disconnectSocket = () => trafficWS.disconnect();