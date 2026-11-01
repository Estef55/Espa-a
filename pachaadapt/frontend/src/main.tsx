import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/service-worker.js").catch(console.error);
  });
}
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
