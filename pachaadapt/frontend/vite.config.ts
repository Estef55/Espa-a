import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El navegador consume /api en el mismo origen. Vite reenvía las peticiones
// al backend local, evitando errores de CORS durante desarrollo y pruebas LAN.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  preview: { host: "0.0.0.0", port: 4173, strictPort: true },
});
