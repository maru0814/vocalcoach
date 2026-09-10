"use client";

import { useEffect, useRef, useState } from "react";
import { CoachAvatar } from "@/components/character/Coach";
import type { CoachPoseName } from "@/components/character/Coach";

// 記事セクション見出しに添えるイラスト（docs/72 §5-2 追補）。
// タイプ×セクション専用イラスト /voice-types/sections/{typeId}/{sectionId}.png があればそれを表示し、
// 未制作の間はソラ先生のポーズ画像に自動フォールバックする（VoiceTypeArt と同じ方式）。
// → イラストが出来たタイプ・セクションから順次差し替わる。コード変更は不要。
export function SectionArt({
  typeId,
  sectionId,
  pose,
  size = 72,
}: {
  typeId: string;
  sectionId: string;
  pose: CoachPoseName;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  // ハイドレーション前に 404 した画像は onError を取り逃すため、マウント時に実体を確認
  useEffect(() => {
    const img = imgRef.current;
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, []);

  if (failed) {
    return <CoachAvatar pose={pose} size={size} />;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={imgRef}
      src={`/voice-types/sections/${typeId}/${sectionId}.png`}
      alt=""
      aria-hidden
      onError={() => setFailed(true)}
      width={size}
      height={size}
      className="shrink-0 object-contain drop-shadow-[0_12px_24px_rgba(15,10,46,0.35)]"
      style={{ width: size, height: size }}
    />
  );
}
