import { createRequire } from "node:module";
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

const require = createRequire(import.meta.url);
const security = require("eslint-plugin-security");
const sonarjs = require("eslint-plugin-sonarjs");
const noUnsanitized = require("eslint-plugin-no-unsanitized");

/** @type {import('eslint').Linter.Config[]} */
export default [
  { ignores: ["dist", "coverage"] },
  // sonarjs v3 + security v4 already ship flat config format
  sonarjs.configs.recommended,
  security.configs.recommended,
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      // no-unsanitized uses legacy eslintrc format — register manually
      "no-unsanitized": noUnsanitized,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-unsanitized/property": "error",
      "no-unsanitized/method": "error",
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "sonarjs/cognitive-complexity": "warn",
      "sonarjs/no-duplicate-string": ["warn", { threshold: 5 }],
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/setupTests.ts"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "sonarjs/no-duplicate-string": "off",
    },
  },
];
