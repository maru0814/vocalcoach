import type { ProfileArtist } from "./types";

// Dramaticタイプの有名人イラスト（docs/62 §11-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。
// 物語性のあるエレガント〜情感トーンで統一。

export const DRAMATIC_ARTISTS: ProfileArtist[] = [
  {
    name: "Aimer",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Aimerのイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 40 Q48 62 52 176 L66 178 L64 62 Z" fill="#1c1a20"/>
      <path d="M98 40 Q112 62 108 176 L94 178 L96 62 Z" fill="#1c1a20"/>
      <polygon points="57,78 62,80 59,150" fill="#2c2934"/>
      <polygon points="103,78 98,80 101,150" fill="#2c2934"/>
      <polygon points="64,74 96,74 104,182 56,182" fill="#211e26"/>
      <polygon points="64,74 78,74 70,150" fill="#2e2b36"/>
      <path d="M62 118 L98 118" stroke="#3a3644" stroke-width="1.6"/>
      <path d="M66 82 L58 118" stroke="#211e26" stroke-width="9" stroke-linecap="round"/>
      <path d="M58 118 Q64 122 68 116" stroke="#211e26" stroke-width="9" stroke-linecap="round" fill="none"/>
      <path d="M94 82 L102 118" stroke="#211e26" stroke-width="9" stroke-linecap="round"/>
      <path d="M102 118 Q96 122 92 116" stroke="#211e26" stroke-width="9" stroke-linecap="round" fill="none"/>
      <circle cx="64" cy="120" r="4.5" fill="#f2c9a4"/>
      <circle cx="96" cy="120" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="86" width="6" height="30" rx="3" fill="#3a3a40"/>
      <circle cx="79" cy="86" r="5.5" fill="#9aa0ad"/>
      <circle cx="79" cy="86" r="2.5" fill="#6b7078"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 42 Q54 60 57 78 L67 76 L66 60 Z" fill="#1c1a20"/>
      <path d="M98 42 Q106 60 103 78 L93 76 L94 60 Z" fill="#1c1a20"/>
      <path d="M63 50 Q60 28 80 27 Q100 28 97 50 Q92 36 80 37 Q68 36 63 50 Z" fill="#1c1a20"/>
      <polygon points="68,32 78,29 71,40" fill="#2e2a34"/>
      <path d="M69 50 Q73 52 76 50" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M84 50 Q87 52 91 50" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="80" cy="60" rx="3" ry="3.6" fill="#8a3a44"/>
    </svg>`,
  },
  {
    name: "星野源",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="星野源のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#3a4658" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="62,74 98,74 95,134 65,134" fill="#e0a92e"/>
      <polygon points="74,74 86,74 84,120 76,120" fill="#f2f0ea"/>
      <path d="M75 82 L85 82" stroke="#3a4658" stroke-width="3"/>
      <polygon points="62,74 72,74 66,130 64,130" fill="#c9982a"/>
      <path d="M78 96 L78 106 M82 96 L82 106" stroke="#c9982a" stroke-width="1.4"/>
      <path d="M66 78 L48 62" stroke="#e0a92e" stroke-width="9" stroke-linecap="round"/>
      <circle cx="45" cy="59" r="5.5" fill="#f2c9a4"/>
      <path d="M42 55 L40 51 M45 53 L44 49 M48 53 L49 49" stroke="#f2c9a4" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M94 78 L112 62" stroke="#e0a92e" stroke-width="9" stroke-linecap="round"/>
      <circle cx="115" cy="59" r="5.5" fill="#f2c9a4"/>
      <path d="M118 55 L120 51 M115 53 L116 49 M112 53 L111 49" stroke="#f2c9a4" stroke-width="2.4" stroke-linecap="round"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 30 80 29 Q101 30 98 50 Q94 37 80 38 Q66 37 62 50 Z" fill="#2c2824"/>
      <polygon points="67,34 77,31 71,41" fill="#413b34"/>
      <path d="M68 47 Q73 45 77 47" stroke="#2c2824" stroke-width="1.5" fill="none"/>
      <path d="M83 47 Q87 45 92 47" stroke="#2c2824" stroke-width="1.5" fill="none"/>
      <path d="M71 51 Q73 53 75 51" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M85 51 Q87 53 89 51" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#f0aa9b"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#f0aa9b"/>
      <path d="M73 58 Q80 64 87 58 Q80 62 73 58 Z" fill="#b0566a"/>
    </svg>`,
  },
  {
    name: "アンジェラ・アキ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="アンジェラ・アキのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M63 44 Q52 62 55 140 L67 142 L66 66 Z" fill="#241f26"/>
      <path d="M97 44 Q108 62 105 140 L93 142 L94 66 Z" fill="#241f26"/>
      <path d="M72 136 L70 174 M88 136 L90 174" stroke="#4a5a78" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="10" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="172" width="19" height="10" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="63,74 97,74 96,118 64,118" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
      <polygon points="63,74 72,74 68,118 65,118" fill="#e2dccb"/>
      <polygon points="60,118 100,118 104,140 56,140" fill="#4a5a78"/>
      <rect x="44" y="120" width="72" height="12" rx="2" fill="#26232a"/>
      <path d="M48 120 L48 129 M55 120 L55 129 M62 120 L62 129 M69 120 L69 129 M76 120 L76 129 M83 120 L83 129 M90 120 L90 129 M97 120 L97 129 M104 120 L104 129 M111 120 L111 129" stroke="#f2f0ea" stroke-width="2.4"/>
      <rect x="44" y="118" width="72" height="3" fill="#3a3640"/>
      <path d="M66 78 L54 116" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
      <circle cx="53" cy="119" r="4.5" fill="#f2c9a4"/>
      <path d="M94 78 L106 116" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
      <circle cx="107" cy="119" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 52 Q60 28 80 27 Q100 28 97 52 L80 44 L63 52 Z" fill="#2a2530"/>
      <path d="M63 52 Q61 40 66 40 L78 44 L64 60 Z" fill="#241f26"/>
      <path d="M97 52 Q99 40 94 40 L82 44 L96 60 Z" fill="#241f26"/>
      <rect x="66" y="47" width="12" height="9" rx="2" fill="none" stroke="#2c2824" stroke-width="1.6"/>
      <rect x="82" y="47" width="12" height="9" rx="2" fill="none" stroke="#2c2824" stroke-width="1.6"/>
      <path d="M78 51 L82 51" stroke="#2c2824" stroke-width="1.6"/>
      <circle cx="72" cy="51.5" r="1.5" fill="#3b3630"/>
      <circle cx="88" cy="51.5" r="1.5" fill="#3b3630"/>
      <path d="M76 59 Q80 62 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "菅田将暉",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="菅田将暉のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#2c2c30" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#3a3a40"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#3a3a40"/>
      <polygon points="61,74 99,74 96,134 64,134" fill="#5a4a3a"/>
      <polygon points="61,74 72,74 66,134 64,134" fill="#6b5a46"/>
      <polygon points="74,74 86,74 84,120 76,120" fill="#e6ddcb"/>
      <path d="M67 82 L70 90 M90 84 L88 92 M65 104 L69 110 M92 106 L88 112 M70 120 L74 126 M88 122 L84 128" stroke="#463828" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M75 84 L78 92 M83 84 L80 92" stroke="#7a6850" stroke-width="1.4"/>
      <path d="M65 78 L48 62" stroke="#5a4a3a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="45" cy="59" r="5" fill="#f2c9a4"/>
      <path d="M95 78 L98 100" stroke="#5a4a3a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="99" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M61 52 Q57 28 80 27 Q103 28 99 52 Q100 40 92 41 Q94 35 86 39 Q88 34 80 38 Q72 34 74 39 Q66 35 68 41 Q60 40 61 52 Z" fill="#2a2622"/>
      <path d="M60 48 Q57 40 61 36 L64 46 Z" fill="#2a2622"/>
      <circle cx="94" cy="60" r="2" fill="#d4a947"/>
      <circle cx="94" cy="60" r="0.9" fill="#f0d68a"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M68 46 Q73 43 77 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M83 46 Q87 43 92 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "ヨルシカ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="ヨルシカ（suisイメージ）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 60 Q50 90 55 176 L68 178 L66 78 Z" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
      <path d="M98 60 Q110 90 105 176 L92 178 L94 78 Z" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
      <polygon points="66,74 94,74 100,150 60,150" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1.2"/>
      <polygon points="66,74 78,74 70,150" fill="#e6e0d1"/>
      <path d="M60 150 Q80 158 100 150 L102 176 Q80 184 58 176 Z" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
      <path d="M63 100 Q80 106 97 100" stroke="#d8d1bf" stroke-width="1.6" fill="none"/>
      <path d="M61 124 Q80 130 99 124" stroke="#d8d1bf" stroke-width="1.6" fill="none"/>
      <path d="M66 78 L54 116" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <path d="M54 116 L52 130" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <circle cx="52" cy="133" r="4.5" fill="#f2c9a4"/>
      <path d="M94 78 L106 116" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <path d="M106 116 L108 130" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <circle cx="108" cy="133" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="64" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="52" r="16" fill="#f2c9a4"/>
      <path d="M64 54 Q62 40 80 40 Q98 40 96 54 L94 54 Q92 46 80 46 Q68 46 66 54 Z" fill="#8a6a44"/>
      <path d="M65 50 L95 50" stroke="#a3805c" stroke-width="2.5"/>
      <path d="M76 60 Q80 62 84 60" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <ellipse cx="80" cy="66" rx="2.4" ry="1.4" fill="#f0aa9b" opacity="0.7"/>
      <path d="M42 40 Q80 22 118 40 Q118 46 112 46 L48 46 Q42 46 42 40 Z" fill="#e6c98a"/>
      <path d="M42 40 Q80 24 118 40 L118 42 Q80 26 42 42 Z" fill="#d8b56e"/>
      <ellipse cx="80" cy="42" rx="18" ry="7" fill="#e0be7c"/>
      <ellipse cx="80" cy="42" rx="18" ry="7" fill="none" stroke="#c9a45c" stroke-width="1"/>
      <path d="M62 42 Q80 48 98 42 L100 46 Q80 52 60 46 Z" fill="#4a7bb5"/>
      <path d="M96 44 L108 40 L106 48 L112 46 L104 54 Z" fill="#4a7bb5"/>
      <path d="M64 46 Q66 50 68 54 M72 46 L72 56 M80 46 L80 56 M88 46 Q86 50 84 54" stroke="#8a6a44" stroke-width="1.2"/>
    </svg>`,
  },
  {
    name: "レミオロメン",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="レミオロメン（藤巻亮太）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#3a4658" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="62,74 98,74 95,134 65,134" fill="#8fb8d8"/>
      <polygon points="74,74 86,74 84,112 76,112" fill="#eaf1f6"/>
      <path d="M66 76 L96 108" stroke="#6b4b33" stroke-width="4"/>
      <path d="M96 104 L128 78" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="125" y="72" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#c08a4a"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#7a4e26"/>
      <path d="M96 110 L126 82" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M65 78 L60 90" stroke="#8fb8d8" stroke-width="9" stroke-linecap="round"/>
      <circle cx="60" cy="93" r="5" fill="#f2c9a4"/>
      <path d="M95 78 L97 102" stroke="#8fb8d8" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="106" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 50 Q61 31 80 30 Q99 31 97 50 Q93 38 80 39 Q67 38 63 50 Z" fill="#2c2824"/>
      <polygon points="68,35 76,32 71,42" fill="#413b34"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M75 58 Q80 61 85 58" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M30 46 Q33 49 30 52 Q27 49 30 46 Z" fill="#f2b8c6"/>
      <path d="M120 40 Q123 43 120 46 Q117 43 120 40 Z" fill="#f2b8c6"/>
      <path d="M40 96 Q43 99 40 102 Q37 99 40 96 Z" fill="#f2b8c6"/>
      <path d="M124 116 Q127 119 124 122 Q121 119 124 116 Z" fill="#f2b8c6"/>
      <path d="M112 58 Q115 61 112 64 Q109 61 112 58 Z" fill="#f4c6d2"/>
    </svg>`,
  },
];
