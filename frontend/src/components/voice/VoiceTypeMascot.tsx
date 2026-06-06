"use client";

import * as React from "react";

// 8つの声タイプの「キャラクター」マスコット（MBTI診断のような世界観）。
// 絵文字の代わりに、各タイプの性格が伝わるSVGキャラを表示する。
// 顔は白系で、どのグラデ背景にも映えるように設計。

const INK = "#2b3350";
const BLUSH = "#fb7aa6";

/** 全キャラ共通の体（肩〜胴のシルエット）。キャラらしさを出す。 */
function Body({ fill = "#ffffff" }: { fill?: string }) {
  return <path d="M12 64 C12 51 21 46 32 46 C43 46 52 51 52 64 Z" fill={fill} opacity="0.95" />;
}

const MASCOTS: Record<string, React.ReactNode> = {
  // 🔥 Rock — 元気いっぱいのロックスター
  rock: (
    <>
      <Body />
      {/* とがった髪 */}
      <path d="M13 24 L17 9 L22 21 L27 7 L32 20 L37 7 L42 21 L47 9 L51 24 Z" fill="#3a2c46" />
      <ellipse cx="32" cy="34" rx="19" ry="18" fill="#fff" />
      {/* ヘッドバンド */}
      <rect x="13" y="23" width="38" height="5.5" rx="2.7" fill="#ff5a5f" />
      <path d="M49 25 l9 -2 -3 6 z" fill="#ff5a5f" />
      {/* 目（やる気） */}
      <circle cx="25" cy="35" r="3.4" fill={INK} />
      <circle cx="39" cy="35" r="3.4" fill={INK} />
      <circle cx="26.2" cy="33.9" r="1.1" fill="#fff" />
      <circle cx="40.2" cy="33.9" r="1.1" fill="#fff" />
      {/* 歌っている口 */}
      <ellipse cx="32" cy="43" rx="3.8" ry="4.6" fill="#e23b6d" />
      <ellipse cx="32" cy="44.6" rx="2" ry="2" fill="#ffd1dd" />
      {/* 稲妻スター */}
      <path d="M50 11 l1.6 3.2 3.4 .5 -2.5 2.4 .6 3.4 -3.1 -1.6 -3.1 1.6 .6 -3.4 -2.5 -2.4 3.4 -.5 z" fill="#ffe14d" />
    </>
  ),

  // 🎙 Groovy — サングラスのクールな大人
  groovy: (
    <>
      <Body />
      {/* なびく髪 */}
      <path d="M12 30 C12 16 24 11 32 11 C42 11 53 17 52 31 C49 22 41 19 32 19 C23 19 15 22 12 30 Z" fill="#7a4a22" />
      <ellipse cx="32" cy="35" rx="19" ry="18" fill="#fff" />
      {/* サングラス */}
      <rect x="18" y="31" width="12" height="8" rx="4" fill="#23283a" />
      <rect x="34" y="31" width="12" height="8" rx="4" fill="#23283a" />
      <rect x="29" y="33.5" width="6" height="2.2" rx="1.1" fill="#23283a" />
      <circle cx="22" cy="34" r="1.3" fill="#9fb6ff" opacity="0.8" />
      <circle cx="38" cy="34" r="1.3" fill="#9fb6ff" opacity="0.8" />
      {/* ニヤリ */}
      <path d="M27 43 q5 4 10 0" stroke={INK} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* 音符 */}
      <g fill="#fff">
        <circle cx="49" cy="20" r="2.6" />
        <rect x="50.6" y="11" width="1.7" height="9" />
        <path d="M50.6 11 q4 1 4 4 q-2 -2 -4 -2 z" />
      </g>
    </>
  ),

  // 🌤 Pop — 親しみやすい笑顔
  pop: (
    <>
      <Body />
      {/* ふわっと前髪 + はねた毛 */}
      <path d="M14 30 C13 17 24 12 32 12 C41 12 52 17 50 30 C46 23 40 21 32 21 C24 21 18 23 14 30 Z" fill="#caa86a" />
      <path d="M48 16 q7 -3 8 4 q-4 -3 -8 -1 z" fill="#caa86a" />
      <ellipse cx="32" cy="35" rx="19" ry="18" fill="#fff" />
      {/* にこにこ目 */}
      <circle cx="25" cy="34" r="3.4" fill={INK} />
      <circle cx="39" cy="34" r="3.4" fill={INK} />
      <circle cx="26.2" cy="32.9" r="1.1" fill="#fff" />
      <circle cx="40.2" cy="32.9" r="1.1" fill="#fff" />
      {/* ほっぺ */}
      <circle cx="21" cy="40" r="3" fill={BLUSH} opacity="0.5" />
      <circle cx="43" cy="40" r="3" fill={BLUSH} opacity="0.5" />
      {/* 大きな笑顔 */}
      <path d="M25 41 q7 7 14 0" stroke={INK} strokeWidth="2.6" strokeLinecap="round" fill="none" />
      {/* きらきら */}
      <path d="M52 33 l1 2.2 2.2 1 -2.2 1 -1 2.2 -1 -2.2 -2.2 -1 2.2 -1 z" fill="#fff" />
    </>
  ),

  // 🌒 Mysterious — フードをかぶった神秘的な子
  mysterious: (
    <>
      {/* フード（マント） */}
      <path d="M9 64 C9 36 20 26 32 26 C44 26 55 36 55 64 Z" fill="#4b2a86" />
      <path d="M14 64 C14 40 22 31 32 31 C42 31 50 40 50 64 Z" fill="#3a2068" />
      <ellipse cx="32" cy="37" rx="16.5" ry="16" fill="#fff" />
      {/* フードの影 */}
      <path d="M16 33 C20 27 27 25 32 25 C37 25 44 27 48 33 C44 30 38 29 32 29 C26 29 20 30 16 33 Z" fill="#2c1850" />
      {/* 半目（ミステリアス） */}
      <path d="M23 37 q3 2.6 6 0" stroke={INK} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      <path d="M35 37 q3 2.6 6 0" stroke={INK} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* 小さな微笑み */}
      <path d="M29 44 q3 2 6 0" stroke={INK} strokeWidth="2" strokeLinecap="round" fill="none" />
      {/* 三日月 */}
      <path d="M50 16 a6 6 0 1 0 1 9 a4.6 4.6 0 1 1 -1 -9 z" fill="#ffe14d" />
    </>
  ),

  // 💎 Crystal — きらびやかで自信に満ちた子
  crystal: (
    <>
      <Body />
      {/* 流れる髪 */}
      <path d="M13 31 C12 16 24 11 32 11 C42 11 53 16 51 31 C48 22 40 19 32 19 C24 19 16 23 13 31 Z" fill="#2f6f8f" />
      <ellipse cx="32" cy="35" rx="19" ry="18" fill="#fff" />
      {/* 片目スター + 片目クール */}
      <path d="M24 35 l1.1 2.3 2.5 .3 -1.8 1.7 .5 2.5 -2.3 -1.2 -2.3 1.2 .5 -2.5 -1.8 -1.7 2.5 -.3 z" fill="#1bb7d6" />
      <circle cx="39" cy="35" r="3.2" fill={INK} />
      <circle cx="40.1" cy="34" r="1" fill="#fff" />
      {/* 自信の笑み */}
      <path d="M28 43 q4.5 3.5 9 0.6" stroke={INK} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* 額のジュエル */}
      <path d="M32 24 l2.4 2.4 -2.4 2.8 -2.4 -2.8 z" fill="#67e8f9" stroke="#fff" strokeWidth="0.7" />
      {/* きらめき */}
      <path d="M50 28 l.8 1.8 1.8 .8 -1.8 .8 -.8 1.8 -.8 -1.8 -1.8 -.8 1.8 -.8 z" fill="#fff" />
      <circle cx="16" cy="26" r="1.3" fill="#fff" />
    </>
  ),

  // 🎭 Dramatic — 感情豊かで切ない子
  dramatic: (
    <>
      <Body />
      {/* ドラマチックな髪 */}
      <path d="M12 28 C11 14 24 10 32 10 C42 10 54 15 52 30 C48 20 40 18 32 18 C23 18 16 21 12 28 Z" fill="#6b1f6b" />
      <ellipse cx="32" cy="35" rx="19" ry="18" fill="#fff" />
      {/* 上がった眉 */}
      <path d="M21 29 q4 -2.5 8 -0.5" stroke={INK} strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M35 28.5 q4 -2 8 0.5" stroke={INK} strokeWidth="2" strokeLinecap="round" fill="none" />
      {/* 潤んだ目 */}
      <circle cx="25" cy="35" r="3.4" fill={INK} />
      <circle cx="39" cy="35" r="3.4" fill={INK} />
      <circle cx="26.3" cy="33.8" r="1.1" fill="#fff" />
      <circle cx="40.3" cy="33.8" r="1.1" fill="#fff" />
      {/* 涙 */}
      <path d="M25 39 q-1.6 3 0 4.4 q1.6 -1.4 0 -4.4 z" fill="#7dd3fc" />
      {/* 感情のこもった口 */}
      <ellipse cx="32" cy="43.5" rx="3" ry="3.8" fill="#d6447a" />
      {/* 小さなスポットライト */}
      <path d="M50 14 l1 2.4 2.4 1 -2.4 1 -1 2.4 -1 -2.4 -2.4 -1 2.4 -1 z" fill="#ffd9ef" />
    </>
  ),

  // 🍃 Whisper — やわらかく穏やかな子
  whisper: (
    <>
      <Body />
      {/* ふんわり髪 */}
      <path d="M14 31 C13 18 24 13 32 13 C41 13 51 18 50 31 C46 24 40 22 32 22 C24 22 18 24 14 31 Z" fill="#7fd0bb" />
      <ellipse cx="32" cy="35" rx="19" ry="18" fill="#fff" />
      {/* 穏やかな閉じ目 */}
      <path d="M22 35 q3 2.6 6 0" stroke={INK} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      <path d="M36 35 q3 2.6 6 0" stroke={INK} strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* ほっぺ */}
      <circle cx="22" cy="40" r="2.8" fill={BLUSH} opacity="0.45" />
      <circle cx="42" cy="40" r="2.8" fill={BLUSH} opacity="0.45" />
      {/* そっとした口 */}
      <path d="M29.5 43 q2.5 2 5 0" stroke={INK} strokeWidth="2" strokeLinecap="round" fill="none" />
      {/* 新芽の葉 */}
      <path d="M32 18 C32 13 28 11 27 9 C31 10 33 13 32 18 Z" fill="#34d399" />
      <path d="M32 18 C32 14 35 12 37 11 C35 14 34 16 32 18 Z" fill="#10b981" />
    </>
  ),

  // 🌙 Moody — 大人っぽく落ち着いた子
  moody: (
    <>
      <Body />
      {/* つやのある髪 */}
      <path d="M12 32 C11 16 24 11 32 11 C42 11 53 16 52 33 C49 22 41 19 32 19 C23 19 15 23 12 32 Z" fill="#2b3357" />
      <path d="M12 32 C13 26 16 22 20 20 C16 26 15 31 16 38 C13 37 12 35 12 32 Z" fill="#1f2742" />
      <ellipse cx="32" cy="35" rx="19" ry="18" fill="#fff" />
      {/* 半目（ウインク気味） */}
      <path d="M22 35.5 q3.4 -2.6 6.8 0" stroke={INK} strokeWidth="2.6" strokeLinecap="round" fill="none" />
      <circle cx="39" cy="35.5" r="3" fill={INK} />
      <circle cx="40" cy="34.6" r="1" fill="#fff" />
      {/* まつげ */}
      <path d="M42.4 33 l2.4 -1.2" stroke={INK} strokeWidth="1.6" strokeLinecap="round" />
      {/* 落ち着いた口 */}
      <path d="M28 43.5 q4.5 3 8.5 -0.3" stroke="#c2557d" strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* 三日月 */}
      <path d="M50 15 a5.6 5.6 0 1 0 1 8.6 a4.3 4.3 0 1 1 -1 -8.6 z" fill="#ffe6a3" />
    </>
  ),
};

export function VoiceTypeMascot({
  id,
  size = 48,
  className,
}: {
  id: string;
  size?: number;
  className?: string;
}) {
  const content = MASCOTS[id] || MASCOTS.pop;
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-hidden="true"
    >
      {content}
    </svg>
  );
}
