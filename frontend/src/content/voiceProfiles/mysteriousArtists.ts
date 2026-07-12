import type { ProfileArtist } from "./types";

// Mysteriousタイプの有名人イラスト（docs/62 §9-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 翳りのある大人トーン（ダーク衣装・伏し目がち・落ち着いた配色）で統一。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。
// 並び順は女女男の繰り返し（同性3連続を回避）。

export const MYSTERIOUS_ARTISTS: ProfileArtist[] = [
  {
    name: "MISIA",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="MISIAのイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 40 Q42 46 46 74 Q54 66 58 74 Q50 82 54 96 Q62 88 62 100 L70 96 L66 60 Z" fill="#2b2530"/>
      <path d="M100 40 Q118 46 114 74 Q106 66 102 74 Q110 82 106 96 Q98 88 98 100 L90 96 L94 60 Z" fill="#2b2530"/>
      <path d="M72 132 L70 172 M88 132 L90 172" stroke="#3a2f4a" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="12" rx="4" fill="#d4a94a"/>
      <rect x="81" y="170" width="19" height="12" rx="4" fill="#d4a94a"/>
      <polygon points="62,76 98,76 104,134 56,134" fill="#5b3a7a"/>
      <path d="M62 96 L98 96" stroke="#d4a94a" stroke-width="2.5"/>
      <polygon points="80,102 82,108 88,108 83,112 85,118 80,114 75,118 77,112 72,108 78,108" fill="#e8c65a"/>
      <path d="M64 80 L52 60" stroke="#5b3a7a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="51" cy="56" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L108 44" stroke="#5b3a7a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="110" cy="40" r="5.5" fill="#f2c9a4"/>
      <rect x="107" y="20" width="6" height="18" rx="3" fill="#3a3a40" transform="rotate(10 110 29)"/>
      <circle cx="109" cy="18" r="5.5" fill="#c8a24a"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M60 52 Q52 26 80 26 Q108 26 100 52 Q98 38 90 40 Q94 34 86 36 Q88 30 80 34 Q72 30 74 36 Q66 34 70 40 Q62 38 60 52 Z" fill="#2b2530"/>
      <path d="M56 48 Q50 60 56 72 L62 58 Z" fill="#2b2530"/>
      <path d="M104 48 Q110 60 104 72 L98 58 Z" fill="#2b2530"/>
      <circle cx="73" cy="52" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.7" fill="#3b3630"/>
      <path d="M69 47 Q73 45 76 47" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 47 Q87 45 91 47" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="60" rx="3.4" ry="4.2" fill="#8a3a44"/>
    </svg>`,
  },
  {
    name: "宇多田ヒカル",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="宇多田ヒカルのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q52 60 55 132 L67 136 L65 62 Z" fill="#241f26"/>
      <path d="M98 42 Q108 60 105 132 L93 136 L95 62 Z" fill="#241f26"/>
      <path d="M72 134 L70 172 M88 134 L90 172" stroke="#2b2a30" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="11" rx="4" fill="#211e22"/>
      <rect x="81" y="170" width="19" height="11" rx="4" fill="#211e22"/>
      <polygon points="61,74 99,74 96,136 64,136" fill="#33323a"/>
      <polygon points="74,74 86,74 84,116 76,116" fill="#efece3"/>
      <polygon points="74,74 80,74 77,116 76,116" fill="#e0dccd"/>
      <path d="M74 74 L80 92 L86 74" stroke="#4a4952" stroke-width="1.4" fill="none"/>
      <path d="M65 78 L58 104" stroke="#33323a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="57" cy="107" r="4.5" fill="#f2c9a4"/>
      <path d="M95 78 L96 100" stroke="#33323a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="97" cy="104" r="4.5" fill="#f2c9a4"/>
      <rect x="78" y="94" width="5.5" height="14" rx="2.5" fill="#3a3a40"/>
      <circle cx="80.5" cy="112" r="5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 52 Q60 28 80 27 Q100 28 97 52 Q95 40 80 40 Q65 40 63 52 Z" fill="#241f26"/>
      <path d="M80 30 L80 42" stroke="#3a3138" stroke-width="1.6"/>
      <circle cx="73" cy="52" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.7" fill="#3b3630"/>
      <path d="M69 48 Q73 46.5 76 48" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 48 Q87 46.5 91 48" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "米津玄師",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="米津玄師のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 178 M88 132 L90 178" stroke="#1f1e24" stroke-width="10"/>
      <rect x="61" y="176" width="19" height="8" rx="4" fill="#211e22"/>
      <rect x="81" y="176" width="19" height="8" rx="4" fill="#211e22"/>
      <polygon points="60,70 100,70 96,140 64,140" fill="#242229"/>
      <polygon points="60,70 100,70 98,80 62,80" fill="#2f2d36"/>
      <path d="M80 70 L80 138" stroke="#3a3842" stroke-width="1.4"/>
      <path d="M63 74 L56 106" stroke="#242229" stroke-width="9" stroke-linecap="round"/>
      <circle cx="55" cy="109" r="4.5" fill="#f2c9a4"/>
      <path d="M97 74 L104 106" stroke="#242229" stroke-width="9" stroke-linecap="round"/>
      <circle cx="105" cy="109" r="4.5" fill="#f2c9a4"/>
      <rect x="72" y="60" width="16" height="12" fill="#f2c9a4"/>
      <rect x="70" y="55" width="20" height="9" rx="3" fill="#2f2d36"/>
      <circle cx="80" cy="46" r="16" fill="#f2c9a4"/>
      <path d="M60 50 Q56 24 80 23 Q104 24 100 50 Q98 42 92 40 L88 48 Q84 40 80 41 Q76 40 72 48 L68 40 Q62 42 60 50 Z" fill="#211d1a"/>
      <path d="M62 44 Q80 34 98 44" stroke="#2f2a26" stroke-width="4" fill="none"/>
      <path d="M67 40 Q72 36 78 39" stroke="#211d1a" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M82 39 Q88 36 93 40" stroke="#211d1a" stroke-width="5" fill="none" stroke-linecap="round"/>
      <circle cx="73" cy="49" r="1.6" fill="#3b3630"/>
      <circle cx="87" cy="49" r="1.6" fill="#3b3630"/>
      <path d="M77 57 Q80 58 83 57" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "椎名林檎",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="椎名林檎のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 42 Q50 58 54 100 L66 104 L64 62 Z" fill="#1f1a1f"/>
      <path d="M100 42 Q110 58 106 100 L94 104 L96 62 Z" fill="#1f1a1f"/>
      <path d="M72 138 L70 172 M88 138 L90 172" stroke="#8a2530" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="12" rx="4" fill="#211e22"/>
      <rect x="81" y="170" width="19" height="12" rx="4" fill="#211e22"/>
      <polygon points="64,76 96,76 102,140 58,140" fill="#8a1a24"/>
      <polygon points="64,76 78,76 71,116" fill="#a5323c"/>
      <path d="M60 128 L100 128" stroke="#5c0f16" stroke-width="2.5"/>
      <path d="M66 80 L56 106" stroke="#8a1a24" stroke-width="9" stroke-linecap="round"/>
      <circle cx="55" cy="109" r="4.5" fill="#f2c9a4"/>
      <path d="M94 78 L100 100" stroke="#8a1a24" stroke-width="9" stroke-linecap="round"/>
      <circle cx="101" cy="104" r="4.5" fill="#f2c9a4"/>
      <rect x="98" y="88" width="6" height="17" rx="3" fill="#2c2c33"/>
      <circle cx="101" cy="86" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 28 80 27 Q101 28 98 50 L98 42 Q80 42 62 42 Z" fill="#1f1a1f"/>
      <path d="M62 42 L98 42 L98 46 L62 46 Z" fill="#1f1a1f"/>
      <rect x="59" y="46" width="6" height="26" rx="3" fill="#1f1a1f"/>
      <rect x="95" y="46" width="6" height="26" rx="3" fill="#1f1a1f"/>
      <circle cx="73" cy="52" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.7" fill="#3b3630"/>
      <path d="M69 47 Q73 45 76 47" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 47 Q87 45 91 47" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <circle cx="88" cy="58" r="1" fill="#3b3630"/>
      <path d="M75 60 Q80 63 85 60 Q80 58 75 60 Z" fill="#b01e2c"/>
    </svg>`,
  },
  {
    name: "milet",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="miletのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 42 Q48 62 52 148 L66 150 L64 62 Z" fill="#6b6a72"/>
      <path d="M100 42 Q112 62 108 148 L94 150 L96 62 Z" fill="#6b6a72"/>
      <polygon points="57,72 63,74 59,140" fill="#83828c"/>
      <polygon points="103,72 97,74 101,140" fill="#83828c"/>
      <path d="M72 134 L70 174 M88 134 L90 174" stroke="#26252b" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#211e22"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#211e22"/>
      <polygon points="62,76 98,76 96,136 64,136" fill="#26242a"/>
      <path d="M74 76 L80 90 L86 76" stroke="#3d3b43" stroke-width="2" fill="none"/>
      <polygon points="62,76 72,76 67,110" fill="#332f38"/>
      <path d="M64 80 L57 106" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="56" cy="109" r="4.5" fill="#f2c9a4"/>
      <path d="M96 80 L103 106" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="104" cy="109" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 54 Q56 28 80 27 Q104 28 98 54 L96 60 Q98 40 80 40 Q62 40 64 60 Z" fill="#6b6a72"/>
      <path d="M64 60 Q60 76 66 92 L70 78 Z" fill="#6b6a72"/>
      <path d="M96 60 Q100 76 94 92 L90 78 Z" fill="#6b6a72"/>
      <circle cx="73" cy="52" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.7" fill="#3b3630"/>
      <path d="M68 49 L76 49 M84 49 L92 49" stroke="#3b3630" stroke-width="1.4" stroke-linecap="round"/>
      <path d="M77 59 Q80 60.5 83 59" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "藤井風",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="藤井風のイラスト">
      <ellipse cx="80" cy="190" rx="42" ry="6" fill="#dcdce3"/>
      <path d="M74 132 L72 176 M86 132 L88 176" stroke="#cdbfa6" stroke-width="10"/>
      <path d="M68 176 Q72 182 78 178 M82 178 Q88 182 92 176" stroke="#f2c9a4" stroke-width="5" stroke-linecap="round" fill="none"/>
      <polygon points="62,74 98,74 96,134 64,134" fill="#e8dcc4"/>
      <polygon points="62,74 98,74 96,80 64,80" fill="#d8cbb0"/>
      <polygon points="74,74 86,74 84,116 76,116" fill="#c9a86e"/>
      <path d="M74 74 L80 96 L86 74" stroke="#c2b494" stroke-width="1.4" fill="none"/>
      <rect x="100" y="86" width="38" height="15" rx="3" fill="#33313a" transform="rotate(-14 100 86)"/>
      <path d="M104 92 L136 84 M105 96 L137 88" stroke="#efece3" stroke-width="1" transform="rotate(-14 100 86)"/>
      <path d="M102 88 L110 100 M110 86 L118 98 M118 84 L126 96" stroke="#5c5a64" stroke-width="1.4" transform="rotate(-14 100 86)"/>
      <path d="M64 118 Q52 116 46 104" stroke="#33313a" stroke-width="4" fill="none"/>
      <path d="M64 78 L56 100" stroke="#e8dcc4" stroke-width="9" stroke-linecap="round"/>
      <circle cx="55" cy="103" r="4.5" fill="#f2c9a4"/>
      <path d="M96 78 L106 92" stroke="#e8dcc4" stroke-width="9" stroke-linecap="round"/>
      <circle cx="108" cy="94" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="48" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q58 26 80 25 Q102 26 98 50 Q96 38 88 42 Q92 32 80 36 Q68 32 72 42 Q64 38 62 50 Z" fill="#2c2620"/>
      <path d="M60 46 Q56 58 62 66 L66 54 Z" fill="#2c2620"/>
      <path d="M100 46 Q104 58 98 66 L94 54 Z" fill="#2c2620"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M76 57 Q80 59 84 57" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "中森明菜",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="中森明菜のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 40 Q40 50 46 78 Q54 70 60 76 L64 62 Z" fill="#241f22"/>
      <path d="M100 40 Q120 50 114 78 Q106 70 100 76 L96 62 Z" fill="#241f22"/>
      <path d="M62 42 Q52 62 56 132 L67 134 L65 60 Z" fill="#241f22"/>
      <path d="M98 42 Q108 62 104 132 L93 134 L95 60 Z" fill="#241f22"/>
      <path d="M72 132 L70 172 M88 132 L90 172" stroke="#6a2530" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="12" rx="4" fill="#211e22"/>
      <rect x="81" y="170" width="19" height="12" rx="4" fill="#211e22"/>
      <polygon points="62,84 98,84 102,134 58,134" fill="#7a1e28"/>
      <path d="M62 84 Q80 78 98 84 L98 90 Q80 84 62 90 Z" fill="#8a2c36"/>
      <path d="M60 122 L100 122" stroke="#521018" stroke-width="2.5"/>
      <path d="M64 88 L52 66" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="51" cy="62" r="4.5" fill="#f2c9a4"/>
      <path d="M96 88 L108 66" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="109" cy="62" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="56" width="8" height="8" fill="#f2c9a4"/>
      <rect x="74" y="46" width="12" height="18" rx="3" fill="#3a3a40"/>
      <circle cx="80" cy="42" r="6.5" fill="#9aa0ad"/>
      <circle cx="80" cy="48" r="16" fill="#f2c9a4"/>
      <path d="M60 50 Q56 24 80 23 Q104 24 100 50 Q98 32 80 38 Q62 32 60 50 Z" fill="#241f22"/>
      <polygon points="62,30 74,26 66,40" fill="#332c2e"/>
      <polygon points="98,30 86,26 94,40" fill="#332c2e"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M68 45 Q73 42 77 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M83 45 Q87 42 92 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M76 57 Q80 60 84 57" stroke="#a52d38" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "JUJU",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="JUJUのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q50 60 54 140 L67 142 L65 62 Z" fill="#20232f"/>
      <path d="M98 42 Q110 60 106 140 L93 142 L95 62 Z" fill="#20232f"/>
      <path d="M72 138 L70 172 M88 138 L90 172" stroke="#2a2d3c" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="12" rx="4" fill="#1c1e28"/>
      <rect x="81" y="170" width="19" height="12" rx="4" fill="#1c1e28"/>
      <polygon points="64,76 96,76 104,140 56,140" fill="#2a3350"/>
      <polygon points="64,76 78,76 71,116" fill="#38425f"/>
      <path d="M64 96 Q80 102 96 96" stroke="#d4a94a" stroke-width="2.5" fill="none"/>
      <circle cx="80" cy="102" r="2.4" fill="#e8c65a"/>
      <path d="M66 80 L56 106" stroke="#2a3350" stroke-width="9" stroke-linecap="round"/>
      <circle cx="55" cy="109" r="4.5" fill="#f2c9a4"/>
      <path d="M94 80 L104 106" stroke="#2a3350" stroke-width="9" stroke-linecap="round"/>
      <circle cx="105" cy="109" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <circle cx="64" cy="58" r="2.4" fill="#d4a94a"/>
      <circle cx="96" cy="58" r="2.4" fill="#d4a94a"/>
      <path d="M63 50 Q60 28 80 27 Q100 28 97 50 Q95 40 80 40 Q65 40 63 50 Z" fill="#241f22"/>
      <path d="M63 44 Q80 40 97 44 Q95 38 80 38 Q65 38 63 44 Z" fill="#2f292c"/>
      <circle cx="73" cy="52" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.7" fill="#3b3630"/>
      <path d="M69 47 Q73 45 76 47" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 47 Q87 45 91 47" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M76 59 Q80 61 84 59" stroke="#a04a54" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "Vaundy",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Vaundyのイラスト">
      <ellipse cx="80" cy="190" rx="42" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#33313a" stroke-width="11"/>
      <rect x="59" y="172" width="22" height="11" rx="5" fill="#efece3" stroke="#bcb5a4" stroke-width="1"/>
      <rect x="79" y="172" width="22" height="11" rx="5" fill="#efece3" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M59 180 L81 180 M79 180 L101 180" stroke="#b9b2a2" stroke-width="1.6"/>
      <polygon points="56,74 104,74 100,138 60,138" fill="#2c2a30"/>
      <polygon points="56,74 104,74 102,82 58,82" fill="#37343b"/>
      <path d="M70 96 Q80 104 90 96 Q88 108 80 108 Q72 108 70 96 Z" fill="#c0392b"/>
      <circle cx="80" cy="118" r="4" fill="#c0392b"/>
      <path d="M60 78 L50 104" stroke="#2c2a30" stroke-width="10" stroke-linecap="round"/>
      <circle cx="49" cy="107" r="5" fill="#f2c9a4"/>
      <path d="M100 78 L110 104" stroke="#2c2a30" stroke-width="10" stroke-linecap="round"/>
      <circle cx="111" cy="107" r="5" fill="#f2c9a4"/>
      <rect x="76" y="60" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="48" r="16" fill="#f2c9a4"/>
      <circle cx="66" cy="34" r="8" fill="#211d1a"/>
      <circle cx="77" cy="29" r="9" fill="#211d1a"/>
      <circle cx="90" cy="31" r="8.5" fill="#211d1a"/>
      <circle cx="97" cy="40" r="7" fill="#211d1a"/>
      <circle cx="63" cy="44" r="6.5" fill="#211d1a"/>
      <circle cx="98" cy="48" r="6" fill="#211d1a"/>
      <path d="M62 44 Q60 34 72 34 Q88 32 96 42 Q90 38 80 39 Q68 38 62 44 Z" fill="#211d1a"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M77 57 Q80 58 83 57" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
];
