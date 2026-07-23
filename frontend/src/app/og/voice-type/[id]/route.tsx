import { ImageResponse } from "next/server";
import { VOICE_TYPE_META, SITE_URL } from "@/components/voice/voiceTypes";

// 診断結果カードの動的OG画像（docs/28 §11）。
// 背景＝タイプ別モチーフ絵に、タイプ名・総合スコア・説明を焼き込んだ 1200x630 PNG を返す。
// 失敗時は従来の静的OGへ302（カードが壊れない）。
export const runtime = "edge";

// 背景・フォントはビルド時にバンドル（実行時の外部fetch依存を持たない）。
// new URL は webpack の静的解析対象のため、動的パスにせず8タイプぶん列挙する。
const ART: Record<string, URL> = {
  rock: new URL("../../../../../public/voice-types/og/rock.jpg", import.meta.url),
  groovy: new URL("../../../../../public/voice-types/og/groovy.jpg", import.meta.url),
  pop: new URL("../../../../../public/voice-types/og/pop.jpg", import.meta.url),
  mysterious: new URL("../../../../../public/voice-types/og/mysterious.jpg", import.meta.url),
  crystal: new URL("../../../../../public/voice-types/og/crystal.jpg", import.meta.url),
  dramatic: new URL("../../../../../public/voice-types/og/dramatic.jpg", import.meta.url),
  whisper: new URL("../../../../../public/voice-types/og/whisper.jpg", import.meta.url),
  moody: new URL("../../../../../public/voice-types/og/moody.jpg", import.meta.url),
};

// サブセット済み Noto Sans JP Bold（frontend/scripts/subset_og_font.py で再生成）
const FONT_URL = new URL("../../../../assets/og/NotoSansJP-OG-Bold.subset.ttf", import.meta.url);

// カード下帯のアクセント（VTYPE_STYLE の tailwind グラデを hex 化したもの）
const ACCENT: Record<string, [string, string]> = {
  rock: ["#f43f5e", "#f97316"],
  groovy: ["#f59e0b", "#ca8a04"],
  pop: ["#38bdf8", "#06b6d4"],
  mysterious: ["#7c3aed", "#4338ca"],
  crystal: ["#22d3ee", "#3b82f6"],
  dramatic: ["#c026d3", "#7e22ce"],
  whisper: ["#34d399", "#14b8a6"],
  moody: ["#475569", "#312e81"],
};

// CTAに出すサイト表記（ビルド時の NEXT_PUBLIC_SITE_URL 由来。localhost はドメイン表示なし）
const SITE_HOST = (() => {
  try {
    const h = new URL(SITE_URL).host;
    return h.startsWith("localhost") || h.startsWith("127.") ? "" : h;
  } catch {
    return "";
  }
})();

function parseScore(sp: URLSearchParams): number | null {
  const s = sp.get("s");
  return s && /^\d{1,3}$/.test(s) ? Number(s) : null;
}

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const id = params.id;
  const meta = VOICE_TYPE_META[id];
  if (!meta || !ART[id]) {
    return new Response("Not found", { status: 404 });
  }
  try {
    const score = parseScore(new URL(req.url).searchParams);
    const [font, art] = await Promise.all([
      fetch(FONT_URL).then((r) => r.arrayBuffer()),
      fetch(ART[id]).then((r) => r.arrayBuffer()),
    ]);
    const [c1, c2] = ACCENT[id];

    return new ImageResponse(
      (
        <div style={{ width: 1200, height: 630, display: "flex", position: "relative", fontFamily: "NotoSansJP" }}>
          {/* eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text */}
          <img
            src={art as unknown as string}
            width={1200}
            height={630}
            style={{ position: "absolute", top: 0, left: 0, objectFit: "cover" }}
          />
          {/* 上部バッジ */}
          <div
            style={{
              position: "absolute",
              top: 28,
              left: 32,
              display: "flex",
              alignItems: "center",
              backgroundColor: "rgba(0,0,0,0.5)",
              color: "#fff",
              fontSize: 26,
              fontWeight: 700,
              padding: "8px 22px",
              borderRadius: 999,
            }}
          >
            🎤 ソラ先生 声タイプ診断
          </div>
          {/* 下部の結果カード帯 */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              flexDirection: "column",
              padding: "26px 40px 22px",
              background: "linear-gradient(to top, rgba(10,10,18,0.92) 0%, rgba(10,10,18,0.82) 70%, rgba(10,10,18,0) 100%)",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", fontSize: 30, color: "#fff", opacity: 0.85 }}>あなたの声タイプは</div>
                <div style={{ display: "flex", alignItems: "center", marginTop: 2 }}>
                  <span style={{ fontSize: 66, fontWeight: 700, color: "#fff", lineHeight: 1.1 }}>
                    {meta.name} {meta.emoji}
                  </span>
                </div>
              </div>
              {score != null && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    marginLeft: "auto",
                    backgroundColor: "rgba(255,255,255,0.14)",
                    border: `3px solid ${c1}`,
                    borderRadius: 24,
                    padding: "10px 26px",
                  }}
                >
                  <span style={{ fontSize: 28, color: "#fff", opacity: 0.9, marginRight: 12 }}>総合</span>
                  <span style={{ fontSize: 74, fontWeight: 700, color: "#fff", lineHeight: 1 }}>{score}</span>
                  <span style={{ fontSize: 30, color: "#fff", opacity: 0.9, marginLeft: 4 }}>点</span>
                </div>
              )}
            </div>
            <div style={{ display: "flex", marginTop: 12, fontSize: 30, color: "rgba(255,255,255,0.96)" }}>
              {meta.desc}
            </div>
            <div style={{ display: "flex", alignItems: "center", marginTop: 16 }}>
              <div style={{ display: "flex", width: 46, height: 8, borderRadius: 4, background: `linear-gradient(to right, ${c1}, ${c2})` }} />
              <div style={{ display: "flex", marginLeft: 14, fontSize: 25, color: "rgba(255,255,255,0.85)" }}>
                あなたの声も15秒歌うだけで無料診断{SITE_HOST ? ` → ${SITE_HOST}` : ""}
              </div>
            </div>
          </div>
        </div>
      ),
      {
        width: 1200,
        height: 630,
        fonts: [{ name: "NotoSansJP", data: font, weight: 700, style: "normal" }],
      },
    );
  } catch {
    // 生成に失敗しても従来の静的OGでカードは成立させる
    return Response.redirect(`${SITE_URL}/voice-types/og/${id}.jpg`, 302);
  }
}
