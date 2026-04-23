import { useEffect } from "react";
import { useTrafficStore } from "../store/TrafficStore";

export default function useKeyboardShortcuts(
  onStart: () => void,
  onStop: () => void
) {
  const { isRunning } = useTrafficStore();

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Space: Start/Stop
      if (e.code === "Space") {
        e.preventDefault();
        if (isRunning) {
          onStop();
        } else {
          onStart();
        }
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [isRunning, onStart, onStop]);
}