// src/main.tsx

// This is the starting point of the system where every thing behaves 
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import MainDashboard from "./components/MainDashboard";

createRoot(document.getElementById("root")!).render(
  
    <MainDashboard />
 
);