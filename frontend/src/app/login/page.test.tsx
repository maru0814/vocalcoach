import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const { register, login } = vi.hoisted(() => ({ register: vi.fn(), login: vi.fn() }));
vi.mock("@/lib/api", () => ({ register, login }));

// ブランドの装飾コンポーネントは描画に無関係なのでスタブ化。
vi.mock("@/components/brand/Brand", () => ({
  BrandWordmark: () => null,
  LogoMark: () => null,
}));

import LoginPage from "./page";

beforeEach(() => {
  push.mockClear();
  register.mockReset();
  login.mockReset();
});

function submit() {
  fireEvent.submit(document.querySelector("form") as HTMLFormElement);
}

describe("LoginPage", () => {
  it("新規登録モードで register→login し /coach へ遷移する", async () => {
    register.mockResolvedValue({ user_id: 1 });
    login.mockResolvedValue({ access_token: "t" });
    render(<LoginPage />);
    submit();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/coach"));
    expect(register).toHaveBeenCalledTimes(1);
    expect(login).toHaveBeenCalledTimes(1);
  });

  it("登録済みエラーは飲み込んでログインを続行する", async () => {
    register.mockRejectedValue(new Error("Email already registered"));
    login.mockResolvedValue({ access_token: "t" });
    render(<LoginPage />);
    submit();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/coach"));
    expect(login).toHaveBeenCalled();
  });

  it("ログイン失敗時はエラーメッセージを表示し遷移しない", async () => {
    register.mockResolvedValue({ user_id: 1 });
    login.mockRejectedValue(new Error("Invalid credentials"));
    render(<LoginPage />);
    submit();
    expect(
      await screen.findByText(/メールアドレスとパスワードをご確認ください/),
    ).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("モード切替で見出しが変わり、login のみ呼ぶ", async () => {
    login.mockResolvedValue({ access_token: "t" });
    render(<LoginPage />);
    // 初期は新規登録モード
    expect(screen.getByText("はじめましょう")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "ログイン" }));
    expect(screen.getByText("おかえりなさい")).toBeInTheDocument();
    submit();
    await waitFor(() => expect(login).toHaveBeenCalled());
    expect(register).not.toHaveBeenCalled();
  });
});
