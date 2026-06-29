import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// next/navigation の useRouter を差し替え（push を観測する）。
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

// AppHeader はこの画面のロジックと無関係なのでスタブ化（billing 取得等を持ち込まない）。
vi.mock("@/components/AppHeader", () => ({ AppHeader: () => null }));

// vi.mock はファイル先頭へ巻き上げられるため、参照する spy は vi.hoisted で用意する。
const { uploadRecordingChecked } = vi.hoisted(() => ({ uploadRecordingChecked: vi.fn() }));
// LimitReachedError は instanceof 判定に使うので、ファクトリ内で実体クラスを定義して公開する。
vi.mock("@/lib/api", () => {
  class LimitReachedError extends Error {}
  return {
    LimitReachedError,
    uploadRecordingChecked,
    logPaywallEvent: vi.fn(),
    startCheckout: vi.fn(),
  };
});

import { LimitReachedError } from "@/lib/api";
import NewRecordingPage from "./page";

beforeEach(() => {
  push.mockClear();
  uploadRecordingChecked.mockReset();
});

// HTML の required 制約は jsdom が submit をブロックするため、フォームへ直接 submit を
// 投げてコンポーネント自身の検証/送信ロジックを通す。
function submitForm(container: HTMLElement) {
  fireEvent.submit(container.querySelector("form") as HTMLFormElement);
}

async function selectFile() {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  await userEvent.upload(input, new File(["x"], "take.webm", { type: "audio/webm" }));
}

describe("NewRecordingPage", () => {
  it("ファイル未選択で送信するとエラーを出し、アップロードは呼ばない", async () => {
    const { container } = render(<NewRecordingPage />);
    submitForm(container);
    expect(await screen.findByText("音声ファイルを選択してください")).toBeInTheDocument();
    expect(uploadRecordingChecked).not.toHaveBeenCalled();
  });

  it("成功すると一覧へ遷移する", async () => {
    uploadRecordingChecked.mockResolvedValue({ recording_id: 1, status: "analyzing" });
    const { container } = render(<NewRecordingPage />);
    await selectFile();
    submitForm(container);
    await waitFor(() => expect(push).toHaveBeenCalledWith("/recordings"));
  });

  it("402(LIMIT_REACHED) でアップグレードモーダルを表示する", async () => {
    uploadRecordingChecked.mockRejectedValue(new LimitReachedError("LIMIT_REACHED"));
    const { container } = render(<NewRecordingPage />);
    await selectFile();
    submitForm(container);
    expect(await screen.findByText("もっと練習したいあなたへ 🎤")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("その他のエラーはメッセージを表示する", async () => {
    uploadRecordingChecked.mockRejectedValue(new Error("サーバーエラー"));
    const { container } = render(<NewRecordingPage />);
    await selectFile();
    submitForm(container);
    expect(await screen.findByText("サーバーエラー")).toBeInTheDocument();
  });
});
