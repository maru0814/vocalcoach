import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PhaseStepper } from "./PhaseStepper";

describe("PhaseStepper", () => {
  it("フェーズごとに現在地ラベルを出す", () => {
    const { rerender } = render(<PhaseStepper phase="A" />);
    expect(screen.getByText(/弱点さがし/)).toBeInTheDocument();
    rerender(<PhaseStepper phase="done" />);
    expect(screen.getByText(/ひと区切り/)).toBeInTheDocument();
    rerender(<PhaseStepper phase="practice" />);
    expect(screen.getByText(/練習中/)).toBeInTheDocument();
  });

  it("レッスン名が無いときはプレースホルダを出す", () => {
    render(<PhaseStepper phase="A" />);
    expect(screen.getByText("（名称未設定のレッスン）")).toBeInTheDocument();
  });

  it("名前をクリック→入力→Enter で onRename を呼ぶ", async () => {
    const onRename = vi.fn();
    render(<PhaseStepper phase="A" songTitle="曲A" onRename={onRename} />);
    await userEvent.click(screen.getByRole("button"));
    const input = screen.getByDisplayValue("曲A");
    await userEvent.clear(input);
    await userEvent.type(input, "新タイトル{Enter}");
    expect(onRename).toHaveBeenCalledWith("新タイトル");
  });

  it("Escape で編集を取り消す（onRename は呼ばれない）", async () => {
    const onRename = vi.fn();
    render(<PhaseStepper phase="A" songTitle="曲A" onRename={onRename} />);
    await userEvent.click(screen.getByRole("button"));
    await userEvent.type(screen.getByDisplayValue("曲A"), "{Escape}");
    expect(onRename).not.toHaveBeenCalled();
  });

  it("空文字は確定しない", async () => {
    const onRename = vi.fn();
    render(<PhaseStepper phase="A" songTitle="曲A" onRename={onRename} />);
    await userEvent.click(screen.getByRole("button"));
    const input = screen.getByDisplayValue("曲A");
    await userEvent.clear(input);
    await userEvent.type(input, "{Enter}");
    expect(onRename).not.toHaveBeenCalled();
  });

  it("onRename が無ければ編集に入らない", async () => {
    render(<PhaseStepper phase="A" songTitle="曲A" />);
    await userEvent.click(screen.getByRole("button"));
    // 入力欄は現れない
    expect(screen.queryByDisplayValue("曲A")).not.toBeInTheDocument();
  });
});
