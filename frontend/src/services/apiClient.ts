import axios from "axios";
import type {
  SimulationStatus,
  MetricsSnapshot,
  TrafficLight,
} from "../types";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

// ─── Simulation ────────────────────────────────────────────────────────────
export const startSimulation = () =>
  api.post("/api/simulation/start", {}).then((r) => r.data);

export const stopSimulation = () =>
  api.post<{ status: string }>("/api/simulation/stop").then((r) => r.data);

export const getSimulationStatus = () =>
  api.get<SimulationStatus>("/api/simulation/status").then((r) => r.data);

// ─── Metrics ───────────────────────────────────────────────────────────────
export const getCurrentMetrics = () =>
  api
    .get<{ baseline: MetricsSnapshot; rl: MetricsSnapshot }>("/api/metrics/current")
    .then((r) => r.data);

// ─── Control ───────────────────────────────────────────────────────────────
export const getTrafficLights = () =>
  api.get<TrafficLight[]>("/api/control/traffic_lights").then((r) => r.data);

// ─── Health ────────────────────────────────────────────────────────────────
export const checkHealth = () =>
  api.get<{ status: string }>("/health").then((r) => r.data);

// ─── Grouped API objects ───────────────────────────────────────────────────
export const simulationAPI = {
  start:    startSimulation,
  stop:     stopSimulation,
  getStatus: getSimulationStatus,
  setSpeed: (speed: number) =>
    api.post("/api/simulation/set_speed", { speed }).then((r) => r.data),
  getSpeed: () =>
    api.get("/api/simulation/speed").then((r) => r.data),
};

export const controlAPI = {
  getTrafficLights,
};

export const metricsAPI = {
  getCurrent: getCurrentMetrics,
};

export const healthAPI = {
  check: checkHealth,
};

export default api;