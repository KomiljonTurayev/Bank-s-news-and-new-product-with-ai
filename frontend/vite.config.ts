import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  resolve: {
    alias: [{ find: "@", replacement: fileURLToPath(new URL("./src", import.meta.url)) }],
  },
  server: {
    port: 5500,
    proxy: {
      // Backend API — prod'dagi nginx `location /api/` xuddi shuni qiladi,
      // bunda brauzer hech qachon 5500'dan chiqmaydi va dev CORS muammosi
      // umuman maydonga chiqmaydi.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    // Testlar src/ ichida kod yonida yashaydi (*.test.ts/tsx).
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
