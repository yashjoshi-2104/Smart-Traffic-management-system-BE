import type { DualSimState } from "../types";

type Listener = (state: DualSimState) => void;
type StatusListener = (status: "connected" | "disconnected" | "connecting") => void;

class TrafficWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Set<Listener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;
  private url: string;
  private shouldConnect = false;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    this.shouldConnect = true;
    this._connect();
  }

  private _connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.emit("connecting");
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 2000;
      this.emit("connected");
    };

    this.ws.onmessage = (event) => {
  try {
    const data: DualSimState = JSON.parse(event.data);
    console.log("📨 WS message:", JSON.stringify(data).slice(0, 200)); // ← ADD THIS
    this.listeners.forEach((fn) => fn(data));
  } catch {
    console.error("WS parse error", event.data);
  }
};

    this.ws.onclose = () => {
      this.emit("disconnected");
      if (this.shouldConnect) {
        this.reconnectTimer = setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 15000);
          this._connect();
        }, this.reconnectDelay);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    this.shouldConnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  onMessage(fn: Listener) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  onStatusChange(fn: StatusListener) {
    this.statusListeners.add(fn);
    return () => this.statusListeners.delete(fn);
  }

  private emit(status: "connected" | "disconnected" | "connecting") {
    this.statusListeners.forEach((fn) => fn(status));
  }
}

export const trafficWS = new TrafficWebSocket("ws://localhost:8000/ws");
export default trafficWS;