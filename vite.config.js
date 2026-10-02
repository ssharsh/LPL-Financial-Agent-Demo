import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config: runs and builds the React app.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
});
