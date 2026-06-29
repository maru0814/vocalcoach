import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // tsconfig の "@/*" → src/* を解決する。
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  // React 18 の自動ランタイムで JSX を変換（React を明示 import しないコンポーネント向け）。
  esbuild: { jsx: "automatic", jsxImportSource: "react" },
  test: {
    // コンポーネントは DOM が要るので jsdom。api.ts 等のロジックも jsdom で問題なく動く。
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
