import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { submitMessageFeedback } = vi.hoisted(() => ({ submitMessageFeedback: vi.fn() }));
vi.mock("@/lib/api", () => ({ submitMessageFeedback, COACH_API_BASE: "" }));
vi.mock("@/components/character/Coach", () => ({ CoachAvatar: () => null }));

import { MessageBubble } from "./Bubbles";

function msg(over: Record<string, unknown>) {
  return { id: 1, role: "coach", type: "text", text: null, created_at: "x", ...over } as never;
}

beforeEach(() => submitMessageFeedback.mockReset());

describe("MessageBubble", () => {
  it("ユーザーのテキストを表示する", () => {
    render(<MessageBubble m={msg({ role: "user", type: "text", text: "やあ" })} />);
    expect(screen.getByText("やあ")).toBeInTheDocument();
  });

  it("コーチのテキストは feedbackable のときFB導線を出す", () => {
    render(
      <MessageBubble m={msg({ text: "こんにちは" })} sessionId={7} feedbackable />,
    );
    expect(screen.getByText("こんにちは")).toBeInTheDocument();
    expect(screen.getByText("役に立った？")).toBeInTheDocument();
  });

  it("feedbackable でなければFB導線を出さない", () => {
    render(<MessageBubble m={msg({ text: "こんにちは" })} sessionId={7} />);
    expect(screen.queryByText("役に立った？")).not.toBeInTheDocument();
  });

  it("旧カード(feedback)は課題ラベルを淡色メモで表示する", () => {
    render(<MessageBubble m={msg({ type: "feedback", payload: { today_task: { label: "ミックス" } } })} />);
    expect(screen.getByText("（以前の診断メモ）ミックス")).toBeInTheDocument();
  });

  it("旧カード(judge pass)は判定メモを表示する", () => {
    render(<MessageBubble m={msg({ type: "judge", payload: { result: "pass" } })} />);
    expect(screen.getByText("（以前の判定）クリアしていました")).toBeInTheDocument();
  });

  it("アクションチップを描画し、押下で onAction を呼ぶ", async () => {
    const onAction = vi.fn();
    render(
      <MessageBubble
        m={msg({ text: "次は？", payload: { actions: [{ id: "finish", icon: "✅", label: "終わる" }] } })}
        onAction={onAction}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "✅ 終わる" }));
    expect(onAction).toHaveBeenCalledWith("finish");
  });

  it("👍 で up 評価を送信し、お礼を表示する", async () => {
    submitMessageFeedback.mockResolvedValue({ ok: true, rating: "up" });
    render(<MessageBubble m={msg({ text: "やあ" })} sessionId={7} feedbackable />);
    await userEvent.click(screen.getByRole("button", { name: "役に立った" }));
    expect(submitMessageFeedback).toHaveBeenCalledWith(7, 1, "up", undefined, undefined);
    expect(await screen.findByText(/ありがとうございます/)).toBeInTheDocument();
  });

  it("👎 で理由フォームを開き、down 評価を送信する", async () => {
    submitMessageFeedback.mockResolvedValue({ ok: true, rating: "down" });
    render(<MessageBubble m={msg({ text: "やあ" })} sessionId={7} feedbackable />);
    await userEvent.click(screen.getByRole("button", { name: "間違いを指摘" }));
    expect(screen.getByText("どこが気になりましたか？（任意）")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "事実が違う" }));
    await userEvent.click(screen.getByRole("button", { name: "送信" }));
    expect(submitMessageFeedback).toHaveBeenCalledWith(7, 1, "down", "fact", undefined);
  });
});
