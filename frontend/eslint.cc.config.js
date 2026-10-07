import tsParser from "@typescript-eslint/parser";
import sonarjs from "eslint-plugin-sonarjs";

// S3776 ekvivalenti: sonarjs cognitive-complexity, Sonar jiheati chegarasi 15.
// Faqat shu qoida — js.configs.recommended qo'shilmaydi (no-undef shovqini cc hisobotini ko'madi).
export default [
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: "latest", sourceType: "module", ecmaFeatures: { jsx: true } },
      globals: {
        window: "readonly",
        document: "readonly",
        location: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        fetch: "readonly",
        AbortController: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        MessageEvent: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        navigator: "readonly",
        console: "readonly",
      },
    },
    plugins: { sonarjs },
    rules: { "sonarjs/cognitive-complexity": ["error", 15] },
  },
];
