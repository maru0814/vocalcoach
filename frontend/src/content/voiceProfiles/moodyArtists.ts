import type { ProfileArtist } from "./types";

// Sexy（moody）タイプの有名人イラスト（docs/62 §13-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 夜・ベルベットの艶トーン（伏し目がち・低照度の落ち着いた配色）で統一。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。
// バンドはボーカルのソロ立ち姿＋楽器で描く（Mr.Children／クリープハイプ方式）。

export const MOODY_ARTISTS: ProfileArtist[] = [
  {
    name: "Uru",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Uruのイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q50 62 54 158 L67 160 L64 62 Z" fill="#211f26"/>
      <path d="M98 42 Q110 62 106 158 L93 160 L96 62 Z" fill="#211f26"/>
      <polygon points="57,80 62,82 59,150" fill="#2e2b36"/>
      <polygon points="103,80 98,82 101,150" fill="#2e2b36"/>
      <polygon points="64,74 96,74 104,180 56,180" fill="#2a3050"/>
      <polygon points="64,74 78,74 71,120" fill="#333a60"/>
      <path d="M60 128 L100 128" stroke="#1e2340" stroke-width="2"/>
      <path d="M74 168 L74 178 M86 168 L86 178" stroke="#e8c9a4" stroke-width="6" stroke-linecap="round"/>
      <path d="M65 82 L74 128" stroke="#2a3050" stroke-width="8" stroke-linecap="round"/>
      <path d="M95 82 L86 128" stroke="#2a3050" stroke-width="8" stroke-linecap="round"/>
      <circle cx="76" cy="130" r="5" fill="#f2c9a4"/>
      <circle cx="84" cy="130" r="5" fill="#f2c9a4"/>
      <ellipse cx="80" cy="132" rx="8" ry="4" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 52 Q60 28 80 27 Q100 28 97 52 Q94 36 88 38 Q84 44 78 42 Q66 40 63 52 Z" fill="#211f26"/>
      <polygon points="66,34 78,30 70,42" fill="#2e2b34"/>
      <path d="M69 51 Q73 53 76 51" stroke="#3b3630" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M84 51 Q87 53 91 51" stroke="#3b3630" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#e79ba0"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#e79ba0"/>
      <ellipse cx="80" cy="59" rx="2.8" ry="3.2" fill="#b0566a"/>
    </svg>`,
  },
  {
    name: "平井堅",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="平井堅のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 172 M88 132 L90 172" stroke="#1e1c22" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="170" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="61,74 99,74 97,134 63,134" fill="#26242a"/>
      <polygon points="61,74 74,74 69,112" fill="#33313a"/>
      <path d="M80 74 L80 132" stroke="#3a383f" stroke-width="1.4"/>
      <path d="M64 82 L58 108" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#d9a878"/>
      <path d="M96 80 L96 100" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="96" cy="104" r="5" fill="#d9a878"/>
      <rect x="93" y="106" width="6" height="16" rx="3" fill="#3a3a40"/>
      <circle cx="96" cy="126" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#d9a878"/>
      <circle cx="80" cy="50" r="16" fill="#d9a878"/>
      <path d="M63 50 Q61 30 80 29 Q99 30 97 50 Q94 37 80 38 Q66 37 63 50 Z" fill="#2b2724"/>
      <polygon points="67,34 77,31 71,42" fill="#3a352f"/>
      <path d="M68 45 Q72 42 77 45 M83 45 Q88 42 92 45" stroke="#2b2724" stroke-width="2.6" fill="none" stroke-linecap="round"/>
      <path d="M70 50.5 Q73 52 76 50.5" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M84 50.5 Q87 52 90 50.5" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M72 57 Q80 60 88 57" stroke="#2b2724" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <path d="M73 62 Q80 66 87 62" stroke="#2b2724" stroke-width="2" fill="none" stroke-linecap="round"/>
      <path d="M76 60 L84 60" stroke="#4a3b32" stroke-width="1.4"/>
    </svg>`,
  },
  {
    name: "手嶌葵",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="手嶌葵のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q52 62 55 150 L67 152 L64 62 Z" fill="#3a2e26"/>
      <path d="M98 42 Q108 62 105 150 L93 152 L96 62 Z" fill="#3a2e26"/>
      <polygon points="58,80 63,82 60,144" fill="#493a2f"/>
      <polygon points="102,80 97,82 100,144" fill="#493a2f"/>
      <polygon points="64,74 96,74 103,178 57,178" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1.1"/>
      <polygon points="64,74 77,74 70,124" fill="#e6e0d1"/>
      <path d="M74 74 Q80 80 86 74 L88 84 Q80 90 72 84 Z" fill="#8a9a5a"/>
      <path d="M80 78 L74 88 M80 78 L86 88" stroke="#7a8a4c" stroke-width="1.6"/>
      <path d="M58 130 L102 130" stroke="#d6cfbd" stroke-width="1.4"/>
      <path d="M65 82 L74 130" stroke="#f0ece1" stroke-width="8" stroke-linecap="round"/>
      <path d="M95 82 L86 130" stroke="#f0ece1" stroke-width="8" stroke-linecap="round"/>
      <circle cx="76" cy="132" r="5" fill="#f2c9a4"/>
      <circle cx="84" cy="132" r="5" fill="#f2c9a4"/>
      <ellipse cx="80" cy="134" rx="8" ry="4" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 52 Q60 29 80 28 Q100 29 97 52 Q94 37 80 38 Q66 37 63 52 Z" fill="#3a2e26"/>
      <polygon points="66,35 78,31 70,43" fill="#4a3b2e"/>
      <path d="M69 51 Q73 53 76 51" stroke="#3b3630" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M84 51 Q87 53 91 51" stroke="#3b3630" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#f0a9ac"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#f0a9ac"/>
      <ellipse cx="80" cy="59" rx="2.6" ry="3" fill="#b0566a"/>
    </svg>`,
  },
  {
    name: "藤原基央（BUMP OF CHICKEN）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="藤原基央（BUMP OF CHICKEN）のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#2c2c34" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="61,74 99,74 97,134 63,134" fill="#6b7488"/>
      <polygon points="61,74 74,74 69,112" fill="#7c8598"/>
      <path d="M66 78 L96 110" stroke="#2a3050" stroke-width="4"/>
      <path d="M96 104 L122 78" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="72" width="9" height="9" rx="2" fill="#3a3050"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#2a3560"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#1c2440"/>
      <path d="M96 110 L120 84" stroke="#4a5680" stroke-width="0.8"/>
      <path d="M64 82 L58 108" stroke="#6b7488" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L98 100" stroke="#6b7488" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q60 30 80 29 Q100 30 98 52 Q95 36 80 37 Q65 36 62 52 Z" fill="#26241f"/>
      <polygon points="66,35 77,31 70,43" fill="#35322b"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M76 59 L84 59" stroke="#8a4a44" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "山下達郎",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="山下達郎のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#2c2c34" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="61,74 99,74 97,134 63,134" fill="#2f7d7a"/>
      <polygon points="61,74 74,74 69,112" fill="#369a94"/>
      <circle cx="72" cy="88" r="1.6" fill="#eef4f0"/>
      <circle cx="86" cy="94" r="1.6" fill="#eef4f0"/>
      <circle cx="76" cy="106" r="1.6" fill="#eef4f0"/>
      <circle cx="90" cy="112" r="1.6" fill="#eef4f0"/>
      <circle cx="70" cy="120" r="1.6" fill="#eef4f0"/>
      <path d="M66 78 L96 110" stroke="#6b4b33" stroke-width="4"/>
      <path d="M96 104 L122 80" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="74" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#c08a4a"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#7a4e26"/>
      <path d="M96 110 L120 86" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M64 82 L58 108" stroke="#2f7d7a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L98 100" stroke="#2f7d7a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M60 54 Q57 34 80 30 Q103 34 100 54 L96 60 Q98 44 80 42 Q62 44 64 60 Z" fill="#33302e"/>
      <path d="M80 30 L80 42" stroke="#26241f" stroke-width="1.6"/>
      <polygon points="60,54 64,60 58,66" fill="#33302e"/>
      <polygon points="100,54 96,60 102,66" fill="#33302e"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "中島美嘉",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="中島美嘉のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q50 62 54 168 L67 170 L64 62 Z" fill="#1f1c22"/>
      <path d="M98 42 Q110 62 106 168 L93 170 L96 62 Z" fill="#1f1c22"/>
      <polygon points="57,80 62,82 59,150" fill="#2c2830"/>
      <polygon points="103,80 98,82 101,150" fill="#2c2830"/>
      <polygon points="64,74 96,74 104,180 56,180" fill="#18161b"/>
      <polygon points="64,74 78,74 71,124" fill="#24222a"/>
      <path d="M60 128 L100 128" stroke="#0f0e12" stroke-width="2"/>
      <path d="M65 82 L74 130" stroke="#18161b" stroke-width="8" stroke-linecap="round"/>
      <path d="M95 82 L86 130" stroke="#18161b" stroke-width="8" stroke-linecap="round"/>
      <circle cx="76" cy="132" r="5" fill="#f2c9a4"/>
      <circle cx="84" cy="132" r="5" fill="#f2c9a4"/>
      <ellipse cx="80" cy="134" rx="8" ry="4" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 54 Q59 28 80 27 Q101 28 98 54 L98 46 Q98 42 92 42 L68 42 Q62 42 62 46 Z" fill="#1f1c22"/>
      <path d="M64 43 L96 43" stroke="#2c2830" stroke-width="4"/>
      <polygon points="64,54 60,50 60,64" fill="#1f1c22"/>
      <polygon points="96,54 100,50 100,64" fill="#1f1c22"/>
      <path d="M69 50 L76 51 M84 51 L91 50" stroke="#3b3630" stroke-width="2" stroke-linecap="round"/>
      <path d="M69 46 L76 45 M84 45 L91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M75 58 Q80 61 85 58 Q80 56.5 75 58 Z" fill="#c0392b"/>
      <circle cx="87" cy="62" r="1.2" fill="#4a3b32"/>
    </svg>`,
  },
  {
    name: "川崎鷹也",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="川崎鷹也のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#2c2c34" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="61,74 99,74 97,134 63,134" fill="#a34434"/>
      <path d="M68 74 L68 132 M80 74 L80 132 M92 74 L92 132" stroke="#7a2f24" stroke-width="1.6"/>
      <path d="M63 90 L97 90 M63 106 L97 106 M63 122 L97 122" stroke="#7a2f24" stroke-width="1.6"/>
      <path d="M66 78 L96 110" stroke="#6b4b33" stroke-width="4"/>
      <path d="M96 104 L122 80" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="74" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#c08a4a"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#7a4e26"/>
      <path d="M96 110 L120 86" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M64 82 L58 108" stroke="#a34434" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L98 100" stroke="#a34434" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 51 Q60 30 80 29 Q100 30 98 51 Q95 36 80 37 Q65 36 62 51 Z" fill="#26241f"/>
      <polygon points="66,35 77,31 70,43" fill="#35322b"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M70 56 Q74 58 78 56 M82 56 Q86 58 90 56" stroke="#5a4a3a" stroke-width="1.2" fill="none"/>
      <path d="M76 60 Q80 62 84 60" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "絢香",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="絢香のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q50 60 55 150 Q60 156 66 152 L64 62 Z" fill="#5a4330"/>
      <path d="M98 42 Q110 60 105 150 Q100 156 94 152 L96 62 Z" fill="#5a4330"/>
      <polygon points="58,78 63,80 61,140" fill="#6b5340"/>
      <polygon points="102,78 97,80 99,140" fill="#6b5340"/>
      <path d="M74 132 L74 172 M86 132 L86 172" stroke="#e8c9a4" stroke-width="6" stroke-linecap="round"/>
      <rect x="66" y="170" width="12" height="9" rx="4" fill="#26242a"/>
      <rect x="82" y="170" width="12" height="9" rx="4" fill="#26242a"/>
      <polygon points="64,74 96,74 102,134 58,134" fill="#d69a2e"/>
      <polygon points="64,74 77,74 70,116" fill="#e5ad3f"/>
      <path d="M60 128 L100 128" stroke="#b07e22" stroke-width="2"/>
      <path d="M65 80 Q56 92 60 104" stroke="#f2c9a4" stroke-width="8" fill="none" stroke-linecap="round"/>
      <circle cx="61" cy="107" r="4.5" fill="#f2c9a4"/>
      <path d="M95 80 Q104 92 100 104" stroke="#f2c9a4" stroke-width="8" fill="none" stroke-linecap="round"/>
      <circle cx="99" cy="107" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 30 80 29 Q101 30 98 52 Q94 37 80 38 Q66 37 62 52 Z" fill="#5a4330"/>
      <polygon points="66,35 78,31 70,43" fill="#6d543e"/>
      <path d="M69 50 Q73 47 76 50" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M84 50 Q87 47 90 50" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="68" cy="57" rx="2.8" ry="1.7" fill="#f0a9ac"/>
      <ellipse cx="92" cy="57" rx="2.8" ry="1.7" fill="#f0a9ac"/>
      <path d="M74 58 Q80 65 86 58 Q80 63 74 58 Z" fill="#a34246"/>
    </svg>`,
  },
  {
    name: "草野マサムネ（スピッツ）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="草野マサムネ（スピッツ）のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#2c2c34" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="61,74 99,74 97,134 63,134" fill="#b6a8dc"/>
      <polygon points="61,74 74,74 69,112" fill="#c6bce6"/>
      <path d="M66 78 L96 110" stroke="#2a3560" stroke-width="4"/>
      <path d="M96 104 L122 80" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="74" width="9" height="9" rx="2" fill="#3a3050"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#3a6ec0"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#254a86"/>
      <path d="M96 110 L120 86" stroke="#8fb4e8" stroke-width="0.8"/>
      <path d="M64 82 L58 108" stroke="#b6a8dc" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L98 100" stroke="#b6a8dc" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M61 53 Q58 31 80 30 Q102 31 99 53 Q96 40 80 40 Q64 40 61 53 Z" fill="#26241f"/>
      <path d="M62 44 Q70 40 80 41 Q90 40 98 44" stroke="#35322b" stroke-width="2" fill="none"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44.5 76 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 46 Q87 44.5 91 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.4" ry="1.5" fill="#f0a9ac"/>
      <ellipse cx="92" cy="56" rx="2.4" ry="1.5" fill="#f0a9ac"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "秦基博",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="秦基博のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#2c2c34" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="61,74 99,74 97,134 63,134" fill="#2f3a5c"/>
      <polygon points="61,74 74,74 69,112" fill="#3a466e"/>
      <path d="M74 74 Q80 79 86 74" stroke="#232c48" stroke-width="1.6" fill="none"/>
      <path d="M66 78 L96 110" stroke="#6b4b33" stroke-width="4"/>
      <path d="M96 104 L122 80" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="74" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#c08a4a"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#7a4e26"/>
      <path d="M96 110 L120 86" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M64 82 L58 108" stroke="#2f3a5c" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L98 100" stroke="#2f3a5c" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q60 30 80 29 Q100 30 98 52 Q95 36 80 37 Q65 36 62 52 Z" fill="#26241f"/>
      <polygon points="67,35 78,31 71,43" fill="#35322b"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "塩塚モエカ（羊文学）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="塩塚モエカ（羊文学）のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q52 60 56 128 L67 130 L64 62 Z" fill="#26232a"/>
      <path d="M98 42 Q108 60 104 128 L93 130 L96 62 Z" fill="#26232a"/>
      <polygon points="59,78 64,80 62,124" fill="#33303a"/>
      <polygon points="101,78 96,80 98,124" fill="#33303a"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#2c2c34" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="63,74 97,74 95,134 65,134" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1.1"/>
      <polygon points="63,74 75,74 70,120" fill="#e5dfd0"/>
      <path d="M74 74 L74 100 M86 74 L86 100" stroke="#cfc7b4" stroke-width="1.4"/>
      <path d="M66 78 L96 110" stroke="#c8bfae" stroke-width="4"/>
      <path d="M96 104 L122 80" stroke="#a89a80" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="74" width="9" height="9" rx="2" fill="#8a7d64"/>
      <ellipse cx="94" cy="116" rx="17" ry="14" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1.1"/>
      <path d="M84 108 Q94 104 104 110" stroke="#dcd6c6" stroke-width="0.8" fill="none"/>
      <ellipse cx="94" cy="116" rx="7" ry="6" fill="#e4ddcc"/>
      <path d="M64 82 L58 108" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L98 100" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q60 29 80 28 Q100 29 98 52 Q95 36 80 37 Q65 36 62 52 Z" fill="#26232a"/>
      <path d="M64 42 Q72 39 82 40 Q90 39 96 43" stroke="#33303a" stroke-width="2" fill="none"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M77 59 Q80 60.5 83 59" stroke="#b0566a" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "清水依与吏（back number）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="清水依与吏（back number）のイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 174 M88 132 L90 174" stroke="#3a3a40" stroke-width="10"/>
      <rect x="61" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="172" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="60,74 100,74 97,134 63,134" fill="#7c7c84"/>
      <polygon points="60,74 74,74 69,114" fill="#8c8c94"/>
      <path d="M68 74 Q72 80 80 80 Q88 80 92 74" stroke="#66666e" stroke-width="3" fill="none"/>
      <path d="M76 82 L76 92 M84 82 L84 92" stroke="#66666e" stroke-width="1.6"/>
      <circle cx="76" cy="93" r="1.4" fill="#66666e"/>
      <circle cx="84" cy="93" r="1.4" fill="#66666e"/>
      <path d="M64 82 L58 108" stroke="#7c7c84" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L96 100" stroke="#7c7c84" stroke-width="9" stroke-linecap="round"/>
      <circle cx="96" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="93" y="106" width="6" height="16" rx="3" fill="#3a3a40"/>
      <circle cx="96" cy="126" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 51 Q60 30 80 29 Q100 30 98 51 Q95 36 80 37 Q65 36 62 51 Z" fill="#26241f"/>
      <polygon points="66,35 77,31 70,43" fill="#35322b"/>
      <circle cx="73" cy="51" r="5.5" fill="none" stroke="#2c2c30" stroke-width="1.6"/>
      <circle cx="87" cy="51" r="5.5" fill="none" stroke="#2c2c30" stroke-width="1.6"/>
      <path d="M78.5 50 L81.5 50" stroke="#2c2c30" stroke-width="1.6"/>
      <path d="M67.5 49 L62 47 M92.5 49 L98 47" stroke="#2c2c30" stroke-width="1.4"/>
      <circle cx="73" cy="51" r="1.5" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.5" fill="#3b3630"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
];
