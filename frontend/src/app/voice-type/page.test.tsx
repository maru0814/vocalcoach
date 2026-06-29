import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { getMe, analyzeVoiceType } = vi.hoisted(() => ({
  getMe: vi.fn(),
  analyzeVoiceType: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ getMe, analyzeVoiceType }));

// 描画の重い子コンポーネント（画像/集計取得/html2canvas）はスタブ化し、ページのロジックに集中する。
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/components/brand/Brand", () => ({ BrandWordmark: () => null }));
vi.mock("@/components/voice/VoiceTypeResult", () => ({
  VoiceTypeBlock: () => null,
  ShareButtons: () => null,
}));
vi.mock("@/components/voice/VoiceTypeArt", () => ({ VoiceTypeArt: () => null }));
vi.mock("@/components/voice/VoiceTypeStats", () => ({ VoiceTypeStats: () => null }));
vi.mock("@/components/voice/voiceTypes", () => ({ VOICE_TYPE_LIST: [] }));
vi.mock("@/components/coach/Recorder", () => ({ Recorder: class {} }));

import VoiceTypePage from "./page";

beforeEach(() => {
  getMe.mockReset();
  analyzeVoiceType.mockReset();
});

function uploadFile() {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  return userEvent.upload(input, new File(["x"], "voice.webm", { type: "audio/webm" }));
}

describe("VoiceTypePage", () => {
  it("未ログインなら登録導線を出す", async () => {
    getMe.mockRejectedValue(new Error("401"));
    render(<VoiceTypePage />);
    expect(await screen.findByText("まずは無料登録（30秒）から🎤")).toBeInTheDocument();
  });

  it("ログイン済みなら録音/アップロードの導線を出す", async () => {
    getMe.mockResolvedValue({ user_id: 1, email: "a@b.c" });
    render(<VoiceTypePage />);
    expect(await screen.findByRole("button", { name: "🎙 録音して診断する" })).toBeInTheDocument();
  });

  it("音源アップロードで診断し、結果を表示する", async () => {
    getMe.mockResolvedValue({ user_id: 1, email: "a@b.c" });
    analyzeVoiceType.mockResolvedValue({
      voice_type: { id: "rock", name: "Rock Voice", emoji: "🔥", desc: "" },
      score: 80,
    });
    render(<VoiceTypePage />);
    await screen.findByRole("button", { name: "🎙 録音して診断する" });
    await uploadFile();
    await waitFor(() => expect(analyzeVoiceType).toHaveBeenCalled());
    expect(await screen.findByRole("button", { name: "🔁 もう一度診断" })).toBeInTheDocument();
  });

  it("解析が401を返したら登録導線へ切り替える", async () => {
    getMe.mockResolvedValue({ user_id: 1, email: "a@b.c" });
    const err = Object.assign(new Error("unauth"), { status: 401 });
    analyzeVoiceType.mockRejectedValue(err);
    render(<VoiceTypePage />);
    await screen.findByRole("button", { name: "🎙 録音して診断する" });
    await uploadFile();
    expect(await screen.findByText("まずは無料登録（30秒）から🎤")).toBeInTheDocument();
  });
});
