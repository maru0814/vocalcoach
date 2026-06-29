import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { getBillingMe, startCheckout, openPortal } = vi.hoisted(() => ({
  getBillingMe: vi.fn(),
  startCheckout: vi.fn(),
  openPortal: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ getBillingMe, startCheckout, openPortal }));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import SettingsPage from "./page";

beforeEach(() => {
  getBillingMe.mockReset();
  startCheckout.mockReset();
  openPortal.mockReset();
  // jsdom の location 代入未実装を回避。
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { set href(_v: string) {} },
  });
});

const FREE = { billing_enabled: true, plan: "free", period_end: null, analysis_used: 1, analysis_limit: 10 };
const PREMIUM = { billing_enabled: true, plan: "premium", period_end: "2026-07-01T00:00:00Z", analysis_used: 1, analysis_limit: null };

describe("SettingsPage", () => {
  it("プレミアムなら解約導線を出し、ポータルを開く", async () => {
    getBillingMe.mockResolvedValue(PREMIUM);
    openPortal.mockResolvedValue({ url: "https://portal.example/x" });
    render(<SettingsPage />);
    const btn = await screen.findByRole("button", { name: "お支払い・解約の管理" });
    await userEvent.click(btn);
    expect(openPortal).toHaveBeenCalled();
  });

  it("無料プランなら申し込み導線を出し、checkout を開く", async () => {
    getBillingMe.mockResolvedValue(FREE);
    startCheckout.mockResolvedValue({ url: "https://checkout.example/x" });
    render(<SettingsPage />);
    const btn = await screen.findByRole("button", { name: "プレミアムをはじめる" });
    expect(btn).not.toBeDisabled();
    await userEvent.click(btn);
    expect(startCheckout).toHaveBeenCalled();
  });

  it("billing 無効時は申し込みボタンを無効化する", async () => {
    getBillingMe.mockResolvedValue({ ...FREE, billing_enabled: false });
    render(<SettingsPage />);
    const btn = await screen.findByRole("button", { name: "プレミアムをはじめる" });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/申し込みを受け付けていません/)).toBeInTheDocument();
  });

  it("取得失敗時はエラーを表示する", async () => {
    getBillingMe.mockRejectedValue(new Error("ネットワークエラー"));
    render(<SettingsPage />);
    expect(await screen.findByText("ネットワークエラー")).toBeInTheDocument();
  });
});
