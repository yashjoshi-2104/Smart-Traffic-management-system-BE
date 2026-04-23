// ─── WebSocket State ───────────────────────────────────────────────────────
export interface VehicleState {
  id: string;
  x: number;
  y: number;
  speed: number;
  lane: string;
  type: string;
  is_emergency?: boolean;
}

export interface TrafficLightState {
  id: string;
  phase: number;
  state: string;
  time_in_phase: number;
}

export interface SimulationState {
  step: number;
  vehicles: VehicleState[];
  traffic_lights: TrafficLightState[];
  metrics: MetricsSnapshot;
  controller_mode: "fixed" | "rl";
  timestamp: number;
}

export interface DualSimState {
  baseline: SimulationState | null;
  rl: SimulationState | null;
  sync_diff: number;
  is_running: boolean;
}

// ─── Metrics ───────────────────────────────────────────────────────────────
export interface MetricsSnapshot {
  avg_speed: number;
  avg_waiting_time: number;
  queue_length: number;
  throughput: number;
  stopped_ratio: number;
  vehicle_count: number;
  step?: number;
}

export interface MetricsHistory {
  timestamps: number[];
  baseline: {
    avg_speed: number[];
    avg_waiting_time: number[];
    queue_length: number[];
    throughput: number[];
  };
  rl: {
    avg_speed: number[];
    avg_waiting_time: number[];
    queue_length: number[];
    throughput: number[];
  };
}

// ─── API Models ────────────────────────────────────────────────────────────
export interface SimulationStatus {
  is_running: boolean;
  step_count: number;
  rl_mode: string;
  sync_status: Record<string, unknown>;
}

export interface TrafficLight {
  id: string;
  phases?: string[];
  current_phase?: number;
  state?: string;
}

// ─── UI State ──────────────────────────────────────────────────────────────
export type ConnectionStatus = "connected" | "disconnected" | "connecting";