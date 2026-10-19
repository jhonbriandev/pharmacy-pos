import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Configuracion de Vite.
 *
 * En desarrollo el navegador habla con el backend a traves de este proxy, de
 * modo que frontend y API comparten origen. Eso no es un detalle estetico:
 * sin proxy la cookie de sesion seria "de terceros" y Safari la bloquearia.
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.js"],
    css: false,
    restoreMocks: true,
    testTimeout: 20000,
    include: ["src/**/*.test.{js,jsx}"],
    // Las fechas del negocio son de Peru. Fijar la zona horaria hace que una
    // prueba de vencimientos no dependa de donde corre la CI.
    env: { TZ: "America/Lima" },
  },
});
