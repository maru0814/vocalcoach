"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await register(email, password);
      }
      await login(email, password);
      router.push("/recordings");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4 rounded bg-white p-6 shadow">
      <h1 className="text-xl font-bold">{mode === "login" ? "ログイン" : "新規登録"}</h1>
      <form className="space-y-3" onSubmit={onSubmit}>
        <input
          className="w-full rounded border p-2"
          type="email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="w-full rounded border p-2"
          type="password"
          placeholder="password (8文字以上)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-60"
          disabled={loading}
          type="submit"
        >
          {loading ? "送信中..." : mode === "login" ? "ログイン" : "登録してログイン"}
        </button>
      </form>
      <button
        className="text-sm text-blue-700 underline"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        type="button"
      >
        {mode === "login" ? "新規登録はこちら" : "ログインはこちら"}
      </button>
    </div>
  );
}
