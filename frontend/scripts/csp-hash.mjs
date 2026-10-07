// dist/index.html'dagi inline <script> bloklarining sha256 xeshlarini
// security-headers.conf'dagi __INLINE_SCRIPT_HASHES__ o'rniga yozadi.
// Ishlatish: node scripts/csp-hash.mjs dist/index.html security-headers.conf
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const [htmlPath, confPath] = process.argv.slice(2);
const html = readFileSync(htmlPath, "utf8");
const hashes = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(
  m => `'sha256-${createHash("sha256").update(m[1], "utf8").digest("base64")}'`,
);
if (hashes.length === 0) throw new Error(`${htmlPath}: inline skript topilmadi`);
const conf = readFileSync(confPath, "utf8");
if (!conf.includes("'__INLINE_SCRIPT_HASHES__'")) throw new Error(`${confPath}: belgi topilmadi`);
writeFileSync(confPath, conf.replace("'__INLINE_SCRIPT_HASHES__'", hashes.join(" ")));
console.log(`CSP: ${hashes.length} ta inline skript xeshi yozildi`);
