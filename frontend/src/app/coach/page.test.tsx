import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const { listCoachSessions, createCoachSession, renameCoachSession } = vi.hoisted(() => ({
  listCoachSessions: vi.fn(),
  createCoachSession: vi.fn(),
  renameCoachSession: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ listCoachSessions, createCoachSession, renameCoachSession }));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/components/brand/Brand", () => ({
  BrandWordmark: () => null,
  Pill: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

import CoachListPage from "./page";

const SESSION = {
  id: 7, song_title: "サビ練習", phase: "A", current_task: null,
  updated_at: "2026-06-01T10:00:00Z",
};

beforeEach(() => {
  push.mockClear();
  listCoachSessions.mockReset();
  createCoachSession.mockReset();
  renameCoachSession.mockReset();
});

describe("CoachListPage", () => {
  it("セッションが無いと空状態を出す", async () => {
    listCoachSessions.mockResolvedValue([]);
    render(<CoachListPage />);
    expect(await screen.findByText("まだレッスンがありません")).toBeInTheDocument();
  });

  it("セッション一覧を表示する", async () => {
    listCoachSessions.mockResolvedValue([SESSION]);
    render(<CoachListPage />);
    expect(await screen.findByText("サビ練習")).toBeInTheDocument();
  });

  it("読み込み失敗時はエラーを表示する", async () => {
    listCoachSessions.mockRejectedValue(new Error("401"));
    render(<CoachListPage />);
    expect(
      await screen.findByText("読み込みに失敗しました。ログインしてください。"),
    ).toBeInTheDocument();
  });

  it("新規作成すると作成後の最新セッションへ遷移する", async () => {
    listCoachSessions.mockResolvedValueOnce([]).mockResolvedValueOnce([{ ...SESSION, id: 99 }]);
    createCoachSession.mockResolvedValue({});
    render(<CoachListPage />);
    await screen.findByText("まだレッスンがありません");
    await userEvent.click(screen.getByRole("button", { name: /新しいレッスンを始める/ }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/coach/99"));
  });

  it("名前を変更すると renameCoachSession を呼ぶ", async () => {
    listCoachSessions.mockResolvedValue([SESSION]);
    renameCoachSession.mockResolvedValue({});
    render(<CoachListPage />);
    await screen.findByText("サビ練習");
    await userEvent.click(screen.getByRole("button", { name: "名前を変更" }));
    const input = screen.getByDisplayValue("サビ練習");
    await userEvent.clear(input);
    await userEvent.type(input, "新しい名前{Enter}");
    await waitFor(() => expect(renameCoachSession).toHaveBeenCalledWith(7, "新しい名前"));
  });
});
