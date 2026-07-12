"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/site/IconChip";

// タイプ別プロフィールページのSNSシェア導線（X / LINE / リンクコピー）。
// 診断直後のユーザーが「私は◯◯タイプだった」と共有しやすい文面を用意する。
export function ProfileShareButtons({
  typeId,
  nameJa,
  heroTitle,
}: {
  typeId: string;
  nameJa: string;
  heroTitle: string;
}) {
  const [copied, setCopied] = useState(false);
  // 共有URLは絶対URLが必須（X/LINEは相対パスを開けない）。
  // ハイドレーション不整合を避けるため、origin はマウント後に解決する。
  const [origin, setOrigin] = useState("");
  useEffect(() => setOrigin(window.location.origin), []);
  const shareUrl = `${origin}/voice-type/${typeId}`;

  const text =
    `🎤 わたしの声タイプは【${nameJa}】でした！\n` +
    `「${heroTitle}」\n\n` +
    `あなたは何タイプ？15秒歌うだけで無料診断できるよ👇`;
  const hashtags = "声診断,ボイトレ,ソラ先生";

  const xUrl =
    `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}` +
    `&url=${encodeURIComponent(shareUrl)}&hashtags=${encodeURIComponent(hashtags)}`;
  const lineUrl =
    `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(shareUrl)}` +
    `&text=${encodeURIComponent(text)}`;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* クリップボード不可の環境では X/LINE を使ってもらう */
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-center text-sm font-bold text-slate-600">
        結果を友達に見せて「君は何タイプ？」
      </p>
      <div className="flex flex-wrap justify-center gap-2.5">
        <a
          href={xUrl}
          target="_blank"
          rel="noreferrer"
          aria-label="Xでシェアする"
          className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-2.5 text-sm font-bold text-white transition hover:brightness-110 active:scale-95"
        >
          <span aria-hidden="true" className="text-base leading-none">𝕏</span>
          でシェア
        </a>
        <a
          href={lineUrl}
          target="_blank"
          rel="noreferrer"
          aria-label="LINEでシェアする"
          className="inline-flex items-center gap-2 rounded-full bg-[#06C755] px-5 py-2.5 text-sm font-bold text-white transition hover:brightness-105 active:scale-95"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.07.75.22.86.5.1.26.07.66.03.92l-.14.83c-.04.25-.2.98.86.53s5.7-3.36 7.78-5.75C21.3 14.9 22 13.06 22 11c0-4.4-4.5-8-10-8zM8.1 13.4H6.1c-.3 0-.5-.2-.5-.5V9.3c0-.3.2-.5.5-.5s.5.2.5.5v3.1h1.5c.3 0 .5.2.5.5s-.2.5-.5.5zm2-.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V9.3c0-.3.2-.5.5-.5s.5.2.5.5v3.6zm4.6 0c0 .22-.14.4-.34.47-.05.02-.1.03-.16.03-.16 0-.3-.07-.4-.2l-1.85-2.5v2.2c0 .3-.22.5-.5.5s-.5-.2-.5-.5V9.3c0-.22.14-.4.34-.47.05-.02.1-.03.16-.03.15 0 .3.08.4.2l1.85 2.5V9.3c0-.3.22-.5.5-.5s.5.2.5.5v3.6zm3-2.3c.3 0 .5.2.5.5s-.2.5-.5.5h-1.5v.8h1.5c.3 0 .5.2.5.5s-.2.5-.5.5h-2c-.3 0-.5-.2-.5-.5V9.3c0-.3.2-.5.5-.5h2c.3 0 .5.2.5.5s-.2.5-.5.5h-1.5v.8h1.5z" />
          </svg>
          LINE
        </a>
        <button
          type="button"
          onClick={copyLink}
          aria-label="リンクをコピーする"
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-bold text-slate-600 transition hover:bg-slate-50 active:scale-95"
        >
          <Icon
            name={copied ? "check" : "paperclip"}
            size={17}
            className={copied ? "text-emerald-500" : ""}
          />
          {copied ? "コピーしました" : "リンクをコピー"}
        </button>
      </div>
    </div>
  );
}
