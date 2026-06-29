import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const logPaywallEvent = vi.fn();
const startCheckout = vi.fn();
vi.mock("@/lib/api", () => ({
  logPaywallEvent: (...a: unknown[]) => logPaywallEvent(...a),
  startCheckout: () => startCheckout(),
}));

import UpgradeModal from "./UpgradeModal";

beforeEach(() => {
  logPaywallEvent.mockClear();
  startCheckout.mockReset();
});

describe("UpgradeModal", () => {
  it("source に応じた見出しを出し、表示イベントを記録する", () => {
    render(<UpgradeModal source="report" onClose={() => {}} />);
    expect(screen.getByText("録音をもっと深く知りたいあなたへ 🎧")).toBeInTheDocument();
    expect(logPaywallEvent).toHaveBeenCalledWith("paywall_view", "report");
  });

  it("「今はやめておく」で onClose を呼ぶ", async () => {
    const onClose = vi.fn();
    render(<UpgradeModal source="limit" onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: "今はやめておく" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("Escape キーで閉じる", async () => {
    const onClose = vi.fn();
    render(<UpgradeModal source="limit" onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("アップグレード押下で checkout を開始し計測する", async () => {
    // jsdom は実ナビゲーションを未実装なので location.href の代入を差し替える。
    const hrefSetter = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { set href(v: string) { hrefSetter(v); } },
    });
    startCheckout.mockResolvedValue({ url: "https://checkout.example/x" });
    render(<UpgradeModal source="limit" onClose={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "プレミアムをはじめる" }));
    expect(startCheckout).toHaveBeenCalled();
    expect(logPaywallEvent).toHaveBeenCalledWith("checkout_start", "limit");
  });
});
