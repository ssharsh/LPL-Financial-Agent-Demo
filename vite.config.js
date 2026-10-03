import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Vite config: runs and builds the React app, and configures Vitest.
// /api is proxied to the Python backend (npm run backend). 127.0.0.1, not
// localhost, so Node does not resolve to IPv6 ::1 and miss uvicorn.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    // jsdom gives component tests a DOM; logic tests run fine in it too.
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
