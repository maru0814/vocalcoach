// www/index.html を APP_URL 埋め込みで生成する（docs/79 5.1）。
// 使い方: node scripts/gen-www.mjs（CAP_SERVER_URL で本番URLを上書き可能）
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const appUrl = (process.env.CAP_SERVER_URL || "https://sora-vocal-ai.duckdns.org").replace(/\/+$/, "");

new URL(appUrl); // 不正URLなら早期に落とす

const tmpl = readFileSync(join(root, "templates", "index.html.tmpl"), "utf8");
mkdirSync(join(root, "www"), { recursive: true });
writeFileSync(join(root, "www", "index.html"), tmpl.replaceAll("{{APP_URL}}", appUrl));
console.log(`generated www/index.html -> ${appUrl}`);
