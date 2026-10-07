// Xavfsizlik lint darvozasi (TTZ v2 SEC-APP-03) — HTML injektsiyasi +
// brauzerga chiqadigan sirlar. Asosiy `eslint.config.js`dan mustaqil: undagi umumiy
// xsatalar (prettier/import) bu darvozani qiziltiqilmasligi keraks, darvoza o'zi
// ham umumiy lint o'rnini bosmaydi. CI: `npm run lint:security`.
// Nega alohida fayl: ESLint 9 flat config'da `--rule "react/no-danger: error"`
// ishlamaydi — qoida plugin'ni o'zining config obyektida ko'rishi kerak.
import tsParser from "@typescript-eslint/parser";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  { ignores: ["node_modules/**", "dist/**", "coverage/**"] },
  {
    files: ["src/**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaFeatures: { jsx: true }, ecmaVersion: "latest", sourceType: "module" },
    },
    // `react-hooks` plugin'i qoida uchun emas, `/* eslint-disable react-hooks/... */`
    // inline direktivalari "rule not found" bilan uzilmasligi kerak.
    plugins: { react, "react-hooks": reactHooks },
    rules: {
      "react/no-danger": "error",
      "react/no-danger-with-children": "error",
    },
  },
  // --- Kalit manba matniga singmasin -----------------------------------------
  // Bu darvoza shuni taqiqlaydi: qiymat manbaga matn bo'lib yozilsin. `VITE_*`
  // o'zgaruvchilari `vite build` paytida bundle'ga singadi va `dist/assets/*.js`
  // ichida hamisha ochiq o'qiladi (2026-09-29 holatida aynan shunday edi).
  {
    files: ["src/**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: "latest", sourceType: "module" },
    },
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          // URL/shablonga yozilgan QIYMAT (`...?client_secret=abc123`).
          // Intervallash (`${...}`) yoki `params.set(...)` shakllari tuza Maydi:
          // `=`dan keyin alfanumerik kelishi qiymat matn qotganini bildiradi.
          selector:
            "Literal[value=/client_secret=[A-Za-z0-9%]/], TemplateElement[value.raw=/client_secret=[A-Za-z0-9%]/]",
          message:
            "client_secret qiymati manba matniga yozilmaydi, maxfiy qiymatlar faqat backend'da turadi (`VITE_*` ham taqiq).",
        },
        {
          // Obyekt literasida qotib qolgan kalit (`{ client_secret: "..." }`).
          selector: 'Property[key.name="client_secret"][value.type="Literal"]',
          message:
            "client_secret qiymati manba matniga yozilmaydi, maxfiy qiymatlar faqat backend'da turadi.",
        },
        {
          selector: "MemberExpression > Identifier[name=/VITE_[A-Z0-9_]*(SECRET|TOKEN)/]",
          message:
            "VITE_* SECRET/TOKEN o'zgaruvchisi yig'ilgan bundle'ga singadi — bunday o'zgaruvchi o'rniga backend endpointini ishlating.",
        },
      ],
    },
  },
];
