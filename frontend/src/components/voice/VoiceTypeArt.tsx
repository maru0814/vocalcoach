"use client";

import { useEffect, useRef, useState } from "react";
import { VoiceTypeMascot } from "./VoiceTypeMascot";
import { VTYPE_STYLE } from "./voiceTypes";

// 各声タイプのモチーフ画像を表示。/voice-types/{id}.png を読み、
// 画像が無い/失敗した場合は SVGマスコット（グラデ背景）にフォールバックする。
// → 実画像が用意できたタイプは写真に、まだのタイプはマスコットのまま、を自動で切替。
export function VoiceTypeArt({
  id,
  className,
  fallbackMascotSize = 44,
}: {
  id: string;
  className?: string;
  fallbackMascotSize?: number;
}) {
  const [failed, setFailed] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const grad = VTYPE_STYLE[id] || "from-brand-500 to-pink-500";

  // ハイドレーション前に 404 した画像は onError を取り逃すため、マウント時に実体を確認
  useEffect(() => {
    const img = imgRef.current;
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, []);

  if (failed) {
    return (
      <div className={`flex items-center justify-center bg-gradient-to-br ${grad} ${className || ""}`}>
        <VoiceTypeMascot id={id} size={fallbackMascotSize} />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={imgRef}
      src={`/voice-types/${id}.jpg`}
      alt=""
      onError={() => setFailed(true)}
      className={`h-full w-full object-cover ${className || ""}`}
    />
  );
}
