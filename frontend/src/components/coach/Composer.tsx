"use client";

import { useRef, useState } from "react";
import { Recorder } from "./Recorder";

type Props = {
  disabled?: boolean;
  onSendText: (text: string) => void;
  onSendAudio: (blob: Blob, filename: string) => void;
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
      onSendAudio(blob, `recording.${ext}`);
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
    if (f) onSendAudio(f, f.name);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  if (recording) {
    return (
      <div className="flex items-center gap-3 border-t bg-white p-3">
        <span className="flex items-center gap-2 text-rose-600">
          <span className="h-3 w-3 animate-pulse rounded-full bg-rose-500" />
          録音中 {elapsed}s / {MAX_SEC}s
        </span>
        <div className="ml-auto flex gap-2">
          <button onClick={cancelRecording} className="rounded-lg border px-3 py-2 text-sm">
            ✕ キャンセル
          </button>
          <button onClick={stopRecording} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white">
            ■ 停止して送信
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t bg-white p-3">
      {error && <div className="mb-2 text-xs text-rose-600">{error}</div>}
      <div className="flex items-end gap-2">
        <button
          type="button"
          aria-label="録音開始"
          disabled={disabled}
          onClick={startRecording}
          className="rounded-full bg-rose-500 p-2 text-white disabled:opacity-40"
          title="録音"
        >
          🎙
        </button>
        <button
          type="button"
          aria-label="ファイルを選ぶ"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          className="rounded-full border p-2 disabled:opacity-40"
          title="アップロード"
        >
          📎
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={onFile}
          className="hidden"
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submitText();
            }
          }}
          rows={1}
          placeholder="メッセージを入力（曲URL・区間など）"
          disabled={disabled}
          className="max-h-32 flex-1 resize-none rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-40"
        />
        <button
          onClick={submitText}
          disabled={disabled || !text.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-40"
        >
          送信
        </button>
      </div>
    </div>
  );
}
