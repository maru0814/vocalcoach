"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BillingMe,
  getBillingMe,
  LimitReachedError,
  uploadRecordingChecked,
} from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

export default function NewRecordingPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [me, setMe] = useState<BillingMe | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setMe(await getBillingMe());
      } catch {
        /* バッジは出せなくてもアップロード自体は可能 */
      }
    })();
  }, []);

  // 残回数バッジ（S-01）。premium / billing無効時は limit=null で非表示。
  const remaining =
    me && me.analysis_limit != null ? Math.max(0, me.analysis_limit - me.analysis_used) : null;
  const limitReached = remaining === 0;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("音声ファイルを選択してください");
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
      router.push("/recordings");
    } catch (err) {
      if (err instanceof LimitReachedError) {
        setShowUpgrade(true); // S-02 上限到達モーダル
      } else {
        setError(err instanceof Error ? err.message : "アップロードに失敗しました");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4 rounded bg-white p-6 shadow">
      <h1 className="text-xl font-bold">録音アップロード</h1>

      {remaining != null ? (
        <p className="text-sm text-gray-600">
          今月の解析 のこり <span className="font-semibold">{remaining}回</span>
          {remaining <= 3 ? (
            <button
              className="ml-2 text-blue-700 underline"
              onClick={() => setShowUpgrade(true)}
            >
              たくさん練習するなら → プレミアム
            </button>
          ) : null}
        </p>
      ) : null}

      <form className="space-y-3" onSubmit={onSubmit}>
        <input
          className="w-full rounded border p-2"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="タイトル"
          required
        />
        <textarea
          className="w-full rounded border p-2"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="メモ（任意）"
          rows={3}
        />
        <input
          className="w-full"
          type="file"
          accept=".wav,.mp3,.m4a,audio/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        {limitReached ? (
          <button
            type="button"
            className="w-full rounded bg-blue-600 px-4 py-2 text-white"
            onClick={() => setShowUpgrade(true)}
          >
            プレミアムで続ける
          </button>
        ) : (
          <button
            className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-60"
            type="submit"
            disabled={loading}
          >
            {loading ? "送信中..." : "アップロード"}
          </button>
        )}
      </form>

      {showUpgrade ? <UpgradeModal source="limit" onClose={() => setShowUpgrade(false)} /> : null}
    </div>
  );
}
