import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // Forward API calls to the Flask backend during development
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true
      }
    }
  }
});
