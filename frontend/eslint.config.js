import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

/**
 * Reglas de lint del frontend.
 *
 * Se enfoca en lo que de verdad causa errores en produccion: dependencias
 * faltantes en hooks, promesas sin manejar y tipos implicitos. El estilo lo
 * resuelve Prettier/el editor, no el lint.
 */
export default tseslint.config(
  { ignores: ["dist", "node_modules", "coverage"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Regla de rendimiento del compilador de React, no de correccion. Se
      // desactiva a proposito: reiniciar el formulario cuando se abre un modal
      // y volver a la pagina 1 cuando cambia un filtro son patrones correctos
      // y mucho mas simples que remontar componentes con `key`.
      "react-hooks/set-state-in-effect": "off",
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
);
