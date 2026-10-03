import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config: runs and builds the React app, and configures Vitest.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
  test: {
    // jsdom gives component tests a DOM; logic tests run fine in it too.
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
