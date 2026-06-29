import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // api.ts は fetch/FormData/Blob（Node18+ のグローバル）だけを使うので node 環境で十分。
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
