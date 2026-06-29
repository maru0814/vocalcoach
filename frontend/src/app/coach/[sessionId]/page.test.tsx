import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({ useParams: () => ({ sessionId: "7" }) }));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const api = vi.hoisted(() => ({
  getCoachSession: vi.fn(),
  sendCoachText: vi.fn(),
  sendCoachAction: vi.fn(),
  sendCoachAudio: vi.fn(),
  uploadCoachReference: vi.fn(),
  renameCoachSession: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

// 子コンポーネントはスタブ化。Composer はコールバックを叩くボタンを露出する。
vi.mock("@/components/coach/Bubbles", () => ({
  MessageBubble: ({ m }: { m: { text?: string | null } }) => <div>{m.text}</div>,
}));
vi.mock("@/components/coach/PhaseStepper", () => ({ PhaseStepper: () => null }));
vi.mock("@/components/character/Coach", () => ({
  CoachAvatar: () => null,
  COACH_NAME: "ソラ先生",
  COACH_ROLE: "ボイストレーナー",
}));
vi.mock("@/components/coach/Composer", () => ({
  Composer: ({
    onSendText,
    onSendAudio,
    disabled,
  }: {
    onSendText: (t: string) => void;
    onSendAudio: (b: Blob, f: string, k: string) => void;
    disabled?: boolean;
  }) => (
    <div>
      <button disabled={disabled} onClick={() => onSendText("テスト発言")}>
        mock-send-text
      </button>
      <button onClick={() => onSendAudio(new Blob(["x"]), "r.webm", "auto")}>mock-send-audio</button>
    </div>
  ),
}));

import CoachChatPage from "./page";

const baseSession = {
  id: 7, song_title: null, song_ref_url: null, user_range: null,
  phase: "A", current_task: null, has_reference: false, messages: [],
};

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset());
});

describe("CoachChatPage", () => {
  it("セッションを読み込み既存メッセージを描画する", async () => {
    api.getCoachSession.mockResolvedValue({
      ...baseSession,
      messages: [{ id: 1, role: "coach", type: "text", text: "はじめまして", created_at: "x" }],
    });
    render(<CoachChatPage />);
    expect(await screen.findByText("はじめまして")).toBeInTheDocument();
  });

  it("読み込み失敗時はエラーを表示する", async () => {
    api.getCoachSession.mockRejectedValue(new Error("401"));
    render(<CoachChatPage />);
    expect(
      await screen.findByText("セッションの読み込みに失敗しました。ログインを確認してください。"),
    ).toBeInTheDocument();
  });

  it("テキスト送信で楽観表示し、コーチ返信を追記する", async () => {
    api.getCoachSession.mockResolvedValue({ ...baseSession });
    api.sendCoachText.mockResolvedValue({
      phase: "A",
      messages: [{ id: 2, role: "coach", type: "text", text: "こんにちは！", created_at: "y" }],
    });
    render(<CoachChatPage />);
    await screen.findByRole("button", { name: "mock-send-text" });
    await userEvent.click(screen.getByRole("button", { name: "mock-send-text" }));
    // 楽観的にユーザー発言が出る
    expect(await screen.findByText("テスト発言")).toBeInTheDocument();
    // コーチ返信も追記される
    expect(await screen.findByText("こんにちは！")).toBeInTheDocument();
    expect(api.sendCoachText).toHaveBeenCalledWith("7", "テスト発言");
  });

  it("送信エラーは JSON message を取り出して表示する", async () => {
    api.getCoachSession.mockResolvedValue({ ...baseSession });
    api.sendCoachText.mockRejectedValue(new Error(JSON.stringify({ message: "混雑しています" })));
    render(<CoachChatPage />);
    await screen.findByRole("button", { name: "mock-send-text" });
    await userEvent.click(screen.getByRole("button", { name: "mock-send-text" }));
    expect(await screen.findByText("混雑しています")).toBeInTheDocument();
  });

  it("お手本ファイルをアップロードすると uploadCoachReference を呼ぶ", async () => {
    api.getCoachSession.mockResolvedValue({ ...baseSession });
    api.uploadCoachReference.mockResolvedValue({ messages: [] });
    render(<CoachChatPage />);
    await screen.findByRole("button", { name: "mock-send-text" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(["x"], "ref.mp3", { type: "audio/mpeg" }));
    await waitFor(() => expect(api.uploadCoachReference).toHaveBeenCalled());
  });
});
