import { create } from "zustand";
import type {
  DualSimState,
  SimulationState,
  MetricsHistory,
  ConnectionStatus,
  TrafficLight,
} from "../types";

interface EmergencyStatus {
  has_emergency: boolean;
  count: number;
  by_direction: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
}

interface EmergencyData {
  baseline: EmergencyStatus;
  rl: EmergencyStatus;
}

const MAX_HISTORY = 60;

interface TrafficStore {
  // Connection
  connectionStatus: ConnectionStatus;
  setConnectionStatus: (s: ConnectionStatus) => void;

  // Simulation running state
  isRunning: boolean;
  setIsRunning: (v: boolean) => void;

  // Latest sim states
  baseline: SimulationState | null;
  rl: SimulationState | null;
  syncDiff: number;

  // Emergency data
  emergency: EmergencyData | null;

  // Traffic lights (fetched from API)
  trafficLights: TrafficLight[];
  setTrafficLights: (tls: TrafficLight[]) => void;

  // Metrics history for charts
  metricsHistory: MetricsHistory;

  // Actions
  applyDualState: (state: DualSimState) => void;
  resetHistory: () => void;
}

const emptyMetrics = (): MetricsHistory => ({
  timestamps: [],
  baseline: { avg_speed: [], avg_waiting_time: [], queue_length: [], throughput: [] },
  rl:       { avg_speed: [], avg_waiting_time: [], queue_length: [], throughput: [] },
});

const push = (arr: number[], val: number) => {
  const next = [...arr, val];
  return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
};

export const useTrafficStore = create<TrafficStore>((set) => ({
  connectionStatus: "disconnected",
  setConnectionStatus: (s) => set({ connectionStatus: s }),

  isRunning: false,
  setIsRunning: (v) => set({ isRunning: v }),

  baseline: null,
  rl:       null,
  syncDiff: 0,
  emergency: null,

  trafficLights: [],
  setTrafficLights: (tls) => set({ trafficLights: tls }),

  metricsHistory: emptyMetrics(),

  applyDualState: (raw: DualSimState) => {
    set((store) => {
      const h   = store.metricsHistory;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const msg = raw as any;

      const emergencyData: EmergencyData | null = msg.emergency ?? null;
      const isBackendFormat = msg.type === "state_update";

      let baseline   = raw.baseline;
      let rl         = raw.rl;
      let isRunning  = raw.is_running ?? true;
      const syncDiff = raw.sync_diff ?? 0;

      if (isBackendFormat) {
        isRunning = true;

        const tlsObj = msg.traffic_lights ?? {};

        const bMetrics = msg.metrics?.baseline ?? {};
        const rMetrics = msg.metrics?.rl ?? {};

        const baselineVehiclesArray = Object.entries(msg.baseline?.vehicles ?? {}).map(
          ([id, v]: [string, any]) => ({
            id,
            x:            v.position?.[0] ?? 0,
            y:            v.position?.[1] ?? 0,
            speed:        v.speed ?? 0,
            lane:         v.lane ?? "",
            type:         v.type ?? "passenger",
            is_emergency: v.is_emergency ?? false,
          })
        );

        const rlVehiclesArray = Object.entries(msg.rl?.vehicles ?? {}).map(
          ([id, v]: [string, any]) => ({
            id,
            x:            v.position?.[0] ?? 0,
            y:            v.position?.[1] ?? 0,
            speed:        v.speed ?? 0,
            lane:         v.lane ?? "",
            type:         v.type ?? "passenger",
            is_emergency: v.is_emergency ?? false,
          })
        );

        const baselineTlsArray = Object.entries(tlsObj).map(([id, val]: [string, any]) => ({
          id,
          phase:         val?.baseline ?? 0,
          state:         String(val?.baseline ?? 0),
          time_in_phase: 0,
        }));

        const rlTlsArray = Object.entries(tlsObj).map(([id, val]: [string, any]) => ({
          id,
          phase:         val?.rl ?? 0,
          state:         String(val?.rl ?? 0),
          time_in_phase: 0,
        }));

        baseline = {
          step:             msg.step ?? 0,
          timestamp:        msg.timestamp ?? Date.now(),
          controller_mode:  "fixed",
          vehicles:         baselineVehiclesArray,
          traffic_lights:   baselineTlsArray,
          metrics: {
            avg_speed:        bMetrics.avg_speed ?? 0,
            avg_waiting_time: bMetrics.avg_waiting_time ?? 0,
            queue_length:     bMetrics.stopped_vehicles ?? 0,
            throughput:       bMetrics.vehicle_count ?? 0,
            stopped_ratio:    bMetrics.stopped_percentage ?? 0,
            vehicle_count:    msg.baseline?.vehicle_count ?? 0,
          },
        };

        rl = {
          step:             msg.step ?? 0,
          timestamp:        msg.timestamp ?? Date.now(),
          controller_mode:  "rl",
          vehicles:         rlVehiclesArray,
          traffic_lights:   rlTlsArray,
          metrics: {
            avg_speed:        rMetrics.avg_speed ?? 0,
            avg_waiting_time: rMetrics.avg_waiting_time ?? 0,
            queue_length:     rMetrics.stopped_vehicles ?? 0,
            throughput:       rMetrics.vehicle_count ?? 0,
            stopped_ratio:    rMetrics.stopped_percentage ?? 0,
            vehicle_count:    msg.rl?.vehicle_count ?? 0,
          },
        };
      }

      if (!baseline && !rl) {
        return { baseline: null, rl: null, syncDiff, isRunning, emergency: emergencyData };
      }

      const bm = baseline?.metrics;
      const rm = rl?.metrics;

      return {
        baseline,
        rl,
        syncDiff,
        isRunning,
        emergency: emergencyData,
        metricsHistory: {
          timestamps: push(h.timestamps, Date.now()),
          baseline: {
            avg_speed:        push(h.baseline.avg_speed,        bm?.avg_speed ?? 0),
            avg_waiting_time: push(h.baseline.avg_waiting_time, bm?.avg_waiting_time ?? 0),
            queue_length:     push(h.baseline.queue_length,     bm?.queue_length ?? 0),
            throughput:       push(h.baseline.throughput,       bm?.throughput ?? 0),
          },
          rl: {
            avg_speed:        push(h.rl.avg_speed,        rm?.avg_speed ?? 0),
            avg_waiting_time: push(h.rl.avg_waiting_time, rm?.avg_waiting_time ?? 0),
            queue_length:     push(h.rl.queue_length,     rm?.queue_length ?? 0),
            throughput:       push(h.rl.throughput,       rm?.throughput ?? 0),
          },
        },
      };
    });
  },

  resetHistory: () =>
    set({ metricsHistory: emptyMetrics(), baseline: null, rl: null, emergency: null }),
}));