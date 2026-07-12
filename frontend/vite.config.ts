import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");
  const backendPort = env.BACKEND_PORT || "8000";
  const frontendPort = Number(env.FRONTEND_PORT || "4173");
  const backendTarget =
    env.VITE_BACKEND_TARGET || `http://127.0.0.1:${backendPort}`;

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: frontendPort,
      proxy: {
        "/api": { target: backendTarget, changeOrigin: true },
        "/health": { target: backendTarget, changeOrigin: true },
        "/ws": {
          target: backendTarget.replace(/^http/, "ws"),
          ws: true,
          changeOrigin: true,
        },
      },
    },
  };
});
