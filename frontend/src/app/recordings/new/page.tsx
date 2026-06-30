"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LimitReachedError,
  uploadRecordingChecked,
} from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { AppHeader } from "@/components/AppHeader";

// バックエンド settings.max_audio_mb と一致（超過は送信前に弾いて具体的な文言を出す）
const MAX_AUDIO_MB = 20;

export default function NewRecordingPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);

  // success を一瞬見せてから一覧へ（無言遷移を避ける／docs/35 課題4）
  useEffect(() => {
    if (!done) return;
    const t = setTimeout(() => router.push("/recordings"), 900);
    return () => clearTimeout(t);
  }, [done, router]);

  function onPickFile(f: File | null) {
    setError("");
    if (f && f.size > MAX_AUDIO_MB * 1024 * 1024) {
      setFile(null);
      setError(`音声ファイルが大きすぎます（最大 ${MAX_AUDIO_MB}MB）。短く録り直すか、別の音源でお試しください。`);
      return;
    }
    setFile(f);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("音声ファイルを選択してください。");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("note", note);
      formData.append("audio_file", file);
      await uploadRecordingChecked(formData);
      setDone(true); // success 状態へ
    } catch (err) {
      if (err instanceof LimitReachedError) {
        setShowUpgrade(true); // S-02 上限到達モーダル
      } else {
        setError(
          err instanceof Error && err.message
            ? err.message
            : "アップロードに失敗しました。通信状態を確かめて、もう一度お試しください。",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-studio min-h-[100dvh]">
      <AppHeader />
      <div className="mx-auto mt-6 max-w-lg px-5">
        <div className="glass space-y-4 rounded-3xl p-6 shadow-card">
          <h1 className="text-xl font-black text-slate-800">録音アップロード</h1>

          {done ? (
            /* success */
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-3xl shadow-soft">
                ✅
              </div>
              <p className="font-bold text-slate-700">アップロードできました！</p>
              <p className="text-sm text-slate-500">評価を準備しています。履歴へ移動します…</p>
            </div>
          ) : (
            <form className="space-y-3" onSubmit={onSubmit}>
              <input
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:border-brand-300 focus:shadow-glow"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="タイトル（例: 残響散歌 サビ）"
                required
              />
              <textarea
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:border-brand-300 focus:shadow-glow"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="メモ（任意）"
                rows={3}
              />
              <label className="block">
                <span className="mb-1 block text-xs font-bold text-slate-500">
                  音声ファイル（wav / mp3 / m4a・最大 {MAX_AUDIO_MB}MB）
                </span>
                <input
                  className="w-full text-sm file:mr-3 file:rounded-full file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-bold file:text-brand-600"
                  type="file"
                  accept=".wav,.mp3,.m4a,audio/*"
                  onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
                  required
                />
              </label>

              {error && (
                <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>
              )}

              <button
                className="w-full rounded-full bg-brand-gradient px-4 py-3 text-sm font-bold text-white shadow-soft transition active:scale-95 disabled:opacity-60"
                type="submit"
                disabled={loading}
              >
                {loading ? "送信中…" : "アップロードして評価する"}
              </button>
            </form>
          )}
        </div>
      </div>

      {showUpgrade && <UpgradeModal source="limit" onClose={() => setShowUpgrade(false)} />}
    </div>
  );
}
