import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";

export type SnippetMessage = { from: "sora" | "user"; text: string };

/**
 * 実物のチャットUIと同じ見た目のミニ製品モック（docs/56 §3-7）。
 * 機能紹介は「アイコン置き」でなく製品そのものを見せる。文体は docs/42 準拠、偽スコアは載せない。
 */
export function ProductSnippet({
  messages,
  className = "",
}: {
  messages: SnippetMessage[];
  className?: string;
}) {
  return (
    <div className={`rounded-2xl bg-white p-3 shadow-card ${className}`}>
      <div className="flex items-center gap-2 border-b border-slate-100 px-1 pb-2">
        <CoachAvatar size={24} />
        <span className="text-xs font-bold text-slate-700">{COACH_NAME}</span>
        <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
          オンライン
        </span>
      </div>
      <div className="space-y-2 px-1 pb-1 pt-3">
        {messages.map((m, i) =>
          m.from === "sora" ? (
            <div key={i} className="flex items-end gap-1.5">
              <CoachAvatar size={20} />
              <p className="max-w-[85%] rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2 text-xs leading-relaxed text-slate-700">
                {m.text}
              </p>
            </div>
          ) : (
            <p
              key={i}
              className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-3 py-2 text-xs leading-relaxed text-white"
            >
              {m.text}
            </p>
          ),
        )}
      </div>
    </div>
  );
}
