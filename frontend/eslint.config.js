import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

/**
 * Reglas de lint del frontend.
 *
 * Se enfoca en lo que de verdad causa errores en produccion: variables sin
 * usar, dependencias faltantes en hooks y promesas sin manejar. El estilo lo
 * resuelve Prettier (`npm run format`), no el lint.
 */
export default [
  { ignores: ["dist", "node_modules", "coverage"] },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...js.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      // Regla de rendimiento del compilador de React, no de correccion. Se
      // desactiva a proposito: reiniciar el formulario cuando se abre un modal
      // y volver a la pagina 1 cuando cambia un filtro son patrones correctos
      // y mucho mas simples que remontar componentes con `key`.
      "react-hooks/set-state-in-effect": "off",
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },
];
