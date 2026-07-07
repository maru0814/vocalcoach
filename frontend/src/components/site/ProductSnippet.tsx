import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";

export type SnippetMsg = { from: "user" | "coach"; text: string };

/**
 * 実物のチャットUIと同じ見た目のミニ製品モック（docs/61 §3-7）。
 * 「グラデ地＋アイコン」パネルの置き換え。端末風フレーム＋実データ調の会話2〜3吹き出し。
 * 文体は実FB（docs/42）準拠。誇張数値・偽スコアは載せない。
 */
export function ProductSnippet({ messages, label }: { messages: SnippetMsg[]; label?: string }) {
  return (
    <div className="relative mx-auto w-full max-w-sm">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-3 shadow-card-2">
        {/* 端末風ヘッダー（実チャット画面と同じ構成） */}
        <div className="flex items-center gap-2 rounded-t-2xl border-b border-slate-100 px-3 pb-2.5 pt-1.5">
          <CoachAvatar size={28} />
          <div className="min-w-0">
            <div className="truncate text-sm font-bold text-slate-800">{COACH_NAME}</div>
            <div className="text-[11px] leading-tight text-slate-400">AIボーカルトレーナー</div>
          </div>
          {label && (
            <span className="ml-auto shrink-0 rounded-full bg-brand-50 px-2.5 py-0.5 text-[11px] font-bold text-brand-700">
              {label}
            </span>
          )}
        </div>
        {/* 会話（実データ調・点数なし） */}
        <div className="space-y-2.5 px-2 pb-2 pt-3">
          {messages.map((m, i) =>
            m.from === "coach" ? (
              <div key={i} className="flex items-end gap-1.5">
                <CoachAvatar size={22} />
                <p className="font-body max-w-[85%] rounded-2xl rounded-bl-md bg-slate-50 px-3.5 py-2 text-[13px] leading-relaxed text-slate-700">
                  {m.text}
                </p>
              </div>
            ) : (
              <div key={i} className="flex justify-end">
                <p className="font-body max-w-[80%] rounded-2xl rounded-br-md bg-brand-600 px-3.5 py-2 text-[13px] leading-relaxed text-white">
                  {m.text}
                </p>
              </div>
            ),
          )}
        </div>
      </div>
    </div>
  );
}
