"use client";

import { useRef, useState } from "react";
import { Recorder } from "./Recorder";

// 録音の種類はユーザーに選ばせず、サーバー側が音声から自動判定する（"auto"）。
type Kind = "song" | "practice" | "auto";

type Props = {
  disabled?: boolean;
  onSendText: (text: string) => void;
  onSendAudio: (blob: Blob, filename: string, kind: Kind) => void;
};

export function Composer({ disabled, onSendText, onSendAudio }: Props) {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<Recorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const MAX_SEC = 60;

  function submitText() {
    const t = text.trim();
    if (!t || disabled) return;
    onSendText(t);
    setText("");
  }

  async function startRecording() {
    setError(null);
    try {
      const rec = new Recorder();
      await rec.start();
      recorderRef.current = rec;
      setRecording(true);
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((e) => {
          if (e + 1 >= MAX_SEC) {
            stopRecording();
            return MAX_SEC;
          }
          return e + 1;
        });
      }, 1000);
    } catch {
      setError("マイクの使用を許可してください");
    }
  }

  async function stopRecording() {
    if (timerRef.current) clearInterval(timerRef.current);
    const rec = recorderRef.current;
    if (!rec) return;
    setRecording(false);
    try {
      const { blob, ext } = await rec.stop();
      onSendAudio(blob, `recording.${ext}`, "auto");
    } catch {
      setError("録音に失敗しました");
    }
    recorderRef.current = null;
  }

  function cancelRecording() {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setRecording(false);
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) onSendAudio(f, f.name, "auto");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const mm = String(Math.floor(elapsed / 60)).padStart(1, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  if (recording) {
    return (
      <div className="glass border-t border-white/40 p-3">
        <div className="flex items-center gap-3 rounded-2xl bg-rose-50 px-4 py-3">
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-rose-400" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500" />
          </span>
          <span className="font-bold text-rose-600">録音中</span>
          <span className="font-mono text-sm text-rose-500">{mm}:{ss} / 1:00</span>
          <div className="ml-auto flex gap-2">
            <button onClick={cancelRecording} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
              ✕
            </button>
            <button onClick={stopRecording} className="rounded-xl bg-brand-gradient px-4 py-2 text-sm font-bold text-white shadow-soft">
              ■ 送信
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass border-t border-white/40 p-3">
      {error && <div className="mb-2 px-1 text-xs text-rose-600">{error}</div>}

      <div className="flex items-end gap-2">
        <button
          type="button"
          aria-label="録音開始"
          disabled={disabled}
          onClick={startRecording}
          title="録音"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-lg text-white shadow-soft transition active:scale-90 disabled:opacity-40"
        >
          🎙
        </button>
        <button
          type="button"
          aria-label="ファイルを選ぶ"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          title="アップロード"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-lg transition active:scale-90 disabled:opacity-40"
        >
          📎
        </button>
        <input ref={fileInputRef} type="file" accept="audio/*" onChange={onFile} className="hidden" />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            // Shift+Enter で送信、Enter は改行
            if (e.key === "Enter" && e.shiftKey) {
              e.preventDefault();
              submitText();
            }
          }}
          rows={1}
          placeholder="メッセージを入力（Shift+Enterで送信）／🎙録音・📎で歌や基礎練を送る"
          disabled={disabled}
          className="max-h-32 flex-1 resize-none rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:shadow-glow disabled:opacity-40"
        />
        <button
          onClick={submitText}
          disabled={disabled || !text.trim()}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-white shadow-soft transition active:scale-90 disabled:opacity-40"
          aria-label="送信"
        >
          ➤
        </button>
      </div>
    </div>
  );
}
