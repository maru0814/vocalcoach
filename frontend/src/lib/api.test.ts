import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getMe,
  login,
  LimitReachedError,
  logPaywallEvent,
  uploadRecordingChecked,
  analyzeVoiceType,
} from "./api";

/** fetch をモックして1回分のレスポンスを差し込む。 */
function mockFetchOnce(opts: {
  ok: boolean;
  status?: number;
  json?: unknown;
  text?: string;
}) {
  const fn = vi.fn().mockResolvedValue({
    ok: opts.ok,
    status: opts.status ?? (opts.ok ? 200 : 400),
    json: async () => opts.json,
    text: async () => opts.text ?? "",
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("request wrapper", () => {
  it("送信先URLと credentials:include を付ける", async () => {
    const fetchMock = mockFetchOnce({ ok: true, json: { user_id: 1, email: "a@b.c" } });
    const me = await getMe();
    expect(me).toEqual({ user_id: 1, email: "a@b.c" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/auth/me");
    expect(init.credentials).toBe("include");
  });

  it("非2xx はレスポンス本文を載せて例外を投げる", async () => {
    mockFetchOnce({ ok: false, status: 401, text: "Not authenticated" });
    await expect(getMe()).rejects.toThrow("Not authenticated");
  });

  it("POST はメソッドとJSONボディを組み立てる", async () => {
    const fetchMock = mockFetchOnce({ ok: true, json: { access_token: "t" } });
    await login("a@b.c", "secret");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ email: "a@b.c", password: "secret" });
  });
});

describe("uploadRecordingChecked", () => {
  it("402(LIMIT_REACHED) を LimitReachedError に変換する", async () => {
    mockFetchOnce({ ok: false, status: 402, text: "LIMIT_REACHED" });
    await expect(uploadRecordingChecked(new FormData())).rejects.toBeInstanceOf(
      LimitReachedError,
    );
  });

  it("他のエラーはそのまま投げる（誤変換しない）", async () => {
    mockFetchOnce({ ok: false, status: 500, text: "boom" });
    await expect(uploadRecordingChecked(new FormData())).rejects.not.toBeInstanceOf(
      LimitReachedError,
    );
  });
});

describe("logPaywallEvent", () => {
  it("計測の失敗は握り潰して UX に影響させない（例外を投げない）", async () => {
    mockFetchOnce({ ok: false, status: 500, text: "fail" });
    await expect(logPaywallEvent("paywall_view", "limit")).resolves.toBeUndefined();
  });
});

describe("analyzeVoiceType", () => {
  it("エラー時は message を取り出し status を載せて投げる", async () => {
    mockFetchOnce({ ok: false, status: 422, json: { message: "声が聞き取れません" } });
    await expect(analyzeVoiceType(new Blob(["x"]))).rejects.toMatchObject({
      message: "声が聞き取れません",
      status: 422,
    });
  });

  it("成功時は診断結果を返す", async () => {
    mockFetchOnce({ ok: true, json: { voice_type: { id: "x", name: "n" }, score: 80 } });
    const res = await analyzeVoiceType(new Blob(["x"]));
    expect(res.score).toBe(80);
  });
});
