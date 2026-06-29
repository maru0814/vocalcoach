// jest-dom のマッチャ（toBeInTheDocument 等）を vitest の expect に追加する。
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom は scrollIntoView を未実装なので no-op で差し替える（チャット画面の自動スクロール等）。
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}
