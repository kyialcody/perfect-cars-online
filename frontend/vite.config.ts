import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on 0.0.0.0 so the dev server is reachable from outside the container
    port: 5173,
    watch: {
      // Bind-mounted source on Docker/Windows doesn't emit native fs events
      // reliably; poll so HMR picks up edits.
      usePolling: true,
    },
  },
});
