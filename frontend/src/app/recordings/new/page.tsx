"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LimitReachedError,
  uploadRecordingChecked,
} from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { AppHeader } from "@/components/AppHeader";

export default function NewRecordingPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);

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
    <>
    <AppHeader />
    <div className="mx-auto max-w-lg space-y-4 rounded bg-white p-6 shadow mt-6">
      <h1 className="text-xl font-bold">録音アップロード</h1>

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
        <button
          className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-60"
          type="submit"
          disabled={loading}
        >
          {loading ? "送信中..." : "アップロード"}
        </button>
      </form>

      {showUpgrade ? <UpgradeModal source="limit" onClose={() => setShowUpgrade(false)} /> : null}
    </div>
    </>
  );
}
