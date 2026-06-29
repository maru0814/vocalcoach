import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Recorder をモック（録音内容は固定 Blob を返す）。
vi.mock("./Recorder", () => ({
  Recorder: class {
    async start() {}
    async stop() {
      return { blob: new Blob(["x"], { type: "audio/webm" }), mimeType: "audio/webm", ext: "webm" };
    }
    cancel() {}
  },
}));

import { Composer } from "./Composer";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("Composer", () => {
  it("テキストを送信すると onSendText が呼ばれ、入力がクリアされる", async () => {
    const onSendText = vi.fn();
    render(<Composer onSendText={onSendText} onSendAudio={vi.fn()} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "  こんにちは  ");
    await userEvent.click(screen.getByRole("button", { name: "送信" }));
    expect(onSendText).toHaveBeenCalledWith("こんにちは");   // trim される
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("空のときは送信ボタンが無効", () => {
    render(<Composer onSendText={vi.fn()} onSendAudio={vi.fn()} />);
    expect(screen.getByRole("button", { name: "送信" })).toBeDisabled();
  });

  it("disabled のとき録音/送信ボタンが無効", () => {
    render(<Composer disabled onSendText={vi.fn()} onSendAudio={vi.fn()} />);
    expect(screen.getByRole("button", { name: "録音開始" })).toBeDisabled();
  });

  it("ファイル選択で onSendAudio(file, name, 'auto') を呼ぶ", async () => {
    const onSendAudio = vi.fn();
    render(<Composer onSendText={vi.fn()} onSendAudio={onSendAudio} />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(["x"], "song.mp3", { type: "audio/mpeg" }));
    expect(onSendAudio).toHaveBeenCalledTimes(1);
    expect(onSendAudio.mock.calls[0][1]).toBe("song.mp3");
    expect(onSendAudio.mock.calls[0][2]).toBe("auto");
  });

  it("録音→送信で onSendAudio が Blob つきで呼ばれる", async () => {
    const onSendAudio = vi.fn();
    render(<Composer onSendText={vi.fn()} onSendAudio={onSendAudio} />);
    await userEvent.click(screen.getByRole("button", { name: "録音開始" }));
    expect(await screen.findByText("録音中")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "■ 送信" }));
    await waitFor(() => expect(onSendAudio).toHaveBeenCalled());
    expect(onSendAudio.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect(onSendAudio.mock.calls[0][2]).toBe("auto");
  });

  it("録音をキャンセルすると通常の入力欄に戻る", async () => {
    render(<Composer onSendText={vi.fn()} onSendAudio={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "録音開始" }));
    await screen.findByText("録音中");
    await userEvent.click(screen.getByRole("button", { name: "✕" }));
    await waitFor(() => expect(screen.getByRole("textbox")).toBeInTheDocument());
  });
});
