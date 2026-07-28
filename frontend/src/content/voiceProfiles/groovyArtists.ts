import type { ProfileArtist } from "./types";

// Groovy（groovy）タイプの有名人イラスト（docs/62 §7-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。
// 並び順は男女交互（同性3連続なし）を厳守。

export const GROOVY_ARTISTS: ProfileArtist[] = [
  {
    name: "あいみょん",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="あいみょんのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 44 Q50 62 54 150 L66 152 L64 64 Z" fill="#2e2c30"/>
      <path d="M98 44 Q110 62 106 150 L94 152 L96 64 Z" fill="#2e2c30"/>
      <path d="M72 136 L70 172 M88 136 L90 172" stroke="#4f6b8c" stroke-width="10"/>
      <rect x="61" y="170" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="170" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="62,74 98,74 95,138 65,138" fill="#e8e2d4"/>
      <polygon points="74,74 86,74 84,110 76,110" fill="#f2efe6"/>
      <path d="M66 76 L92 112" stroke="#8a5a2e" stroke-width="4"/>
      <path d="M92 108 L58 86" stroke="#a67638" stroke-width="5" stroke-linecap="round"/>
      <rect x="49" y="78" width="9" height="9" rx="2" fill="#5c4028"/>
      <ellipse cx="94" cy="118" rx="17" ry="14" fill="#d9a45c"/>
      <ellipse cx="94" cy="118" rx="6.5" ry="5.5" fill="#8a5a2e"/>
      <path d="M92 112 L60 90" stroke="#efe4cf" stroke-width="0.8"/>
      <path d="M65 80 L60 88" stroke="#e8e2d4" stroke-width="9" stroke-linecap="round"/>
      <circle cx="60" cy="90" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L97 104" stroke="#e8e2d4" stroke-width="9" stroke-linecap="round"/>
      <circle cx="96" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 28 80 27 Q101 28 98 52 Q95 36 80 36 Q80 42 80 42 Q80 36 65 36 Q62 40 62 52 Z" fill="#2e2c30"/>
      <path d="M80 33 L80 44" stroke="#211f22" stroke-width="1.4"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="57" rx="2.6" ry="1.6" fill="#f0aeae"/>
      <ellipse cx="92" cy="57" rx="2.6" ry="1.6" fill="#f0aeae"/>
      <path d="M76 58 Q80 61 84 58" stroke="#b0566a" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "桑田佳祐",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="桑田佳祐のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#5a5560" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#3a3540"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#3a3540"/>
      <polygon points="62,74 98,74 95,134 65,134" fill="#3f4a5c"/>
      <polygon points="74,74 86,74 84,120 76,120" fill="#6b6f5a"/>
      <path d="M64 82 L54 108" stroke="#3f4a5c" stroke-width="9" stroke-linecap="round"/>
      <circle cx="53" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 78 L110 54" stroke="#3f4a5c" stroke-width="9" stroke-linecap="round"/>
      <circle cx="112" cy="50" r="5" fill="#f2c9a4"/>
      <rect x="108" y="30" width="6" height="18" rx="3" fill="#2c2c30" transform="rotate(14 111 40)"/>
      <circle cx="109" cy="28" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M64 40 Q62 60 66 58 L67 44 Z" fill="#4a4038"/>
      <path d="M96 40 Q98 60 94 58 L93 44 Z" fill="#4a4038"/>
      <path d="M63 46 Q62 32 80 32 Q98 32 97 46 L94 44 Q92 40 80 40 Q68 40 66 44 Z" fill="#3a332e"/>
      <path d="M62 40 Q80 30 98 40 L98 46 Q88 41 80 41 Q72 41 62 46 Z" fill="#c0392b"/>
      <path d="M62 43 L58 47 M98 43 L102 47" stroke="#c0392b" stroke-width="3" stroke-linecap="round"/>
      <rect x="66" y="49" width="28" height="6" rx="3" fill="#26242a"/>
      <path d="M66 50 L62 48 M94 50 L98 48" stroke="#26242a" stroke-width="1.6"/>
      <path d="M67 60 L76 60 M84 60 L93 60" stroke="#7a6a52" stroke-width="1.4"/>
      <path d="M74 64 Q80 68 86 64" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M45 78 L36 84" stroke="#3f4a5c" stroke-width="9" stroke-linecap="round"/>
      <circle cx="34" cy="86" r="5" fill="#f2c9a4"/>
      <rect x="29" y="60" width="7" height="27" rx="3.5" fill="#2c2c30" transform="rotate(-12 32 74)"/>
      <circle cx="30" cy="57" r="6" fill="#8f95a2"/>
      <circle cx="30" cy="57" r="2.4" fill="#5a606b"/>
    </svg>`,
  },
  {
    name: "Superfly",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Superflyのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 40 Q44 56 50 96 Q46 118 56 138 L68 138 L64 60 Z" fill="#4a3020"/>
      <path d="M100 40 Q116 56 110 96 Q114 118 104 138 L92 138 L96 60 Z" fill="#4a3020"/>
      <path d="M55 74 Q47 90 54 108" stroke="#5c4028" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M105 74 Q113 90 106 108" stroke="#5c4028" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M73 134 L71 168 M87 134 L89 168" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="164" width="18" height="19" rx="5" fill="#c9303c"/>
      <rect x="80" y="164" width="18" height="19" rx="5" fill="#c9303c"/>
      <path d="M63 168 L79 168 M81 168 L97 168" stroke="#8f1f28" stroke-width="1.8"/>
      <polygon points="64,74 96,74 102,136 58,136" fill="#d8404a"/>
      <polygon points="64,74 78,74 71,124" fill="#e2606a"/>
      <path d="M60 122 L100 122" stroke="#a32d2d" stroke-width="2.5"/>
      <path d="M64 80 L52 104" stroke="#d8404a" stroke-width="8" stroke-linecap="round"/>
      <path d="M52 104 Q58 108 62 100" stroke="#d8404a" stroke-width="8" stroke-linecap="round" fill="none"/>
      <circle cx="80" cy="92" r="5" fill="#3a3540"/>
      <path d="M96 80 L108 100" stroke="#d8404a" stroke-width="8" stroke-linecap="round"/>
      <circle cx="110" cy="103" r="5" fill="#f2c9a4"/>
      <rect x="106" y="90" width="6" height="15" rx="3" fill="#3a3a40"/>
      <circle cx="80" cy="86" r="4.5" fill="#8f95a2"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q57 28 80 27 Q103 28 98 52 Q94 38 80 34 Q66 38 62 52 Z" fill="#4a3020"/>
      <path d="M63 42 Q70 34 80 36 Q90 34 97 42 Q88 40 80 42 Q72 40 63 42 Z" fill="#5c4028"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="59" rx="3.4" ry="4.2" fill="#8a3a44"/>
    </svg>`,
  },
  {
    name: "鈴木雅之",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="鈴木雅之のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#1f1e22" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#211f24"/>
      <polygon points="72,74 88,74 84,132 76,132" fill="#33313a"/>
      <polygon points="72,74 80,86 88,74" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M74 78 L80 100 L86 78" stroke="#7d3b3b" stroke-width="3.5" fill="none"/>
      <polygon points="78,88 82,88 80,102" fill="#8a2d2d"/>
      <path d="M63 82 L53 108" stroke="#211f24" stroke-width="9" stroke-linecap="round"/>
      <circle cx="52" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M97 80 L110 56" stroke="#211f24" stroke-width="9" stroke-linecap="round"/>
      <circle cx="112" cy="52" r="5" fill="#f2c9a4"/>
      <rect x="108" y="34" width="6" height="16" rx="3" fill="#2c2c30" transform="rotate(16 111 42)"/>
      <circle cx="109" cy="32" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 48 Q62 30 80 30 Q98 30 97 48 Q90 40 80 41 Q70 40 63 48 Z" fill="#26242a"/>
      <rect x="66" y="52" width="28" height="6" rx="3" fill="#141317"/>
      <path d="M66 53 L62 51 M94 53 L98 51" stroke="#141317" stroke-width="1.6"/>
      <rect x="79" y="52" width="2" height="6" fill="#33313a"/>
      <path d="M70 46 Q73 44 76 46 M84 46 Q87 44 90 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M69 62 L76 62 M84 62 L91 62" stroke="#4a453f" stroke-width="2.2"/>
      <path d="M74 66 Q80 69 86 66" stroke="#7d4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M74 71 L86 71" stroke="#4a453f" stroke-width="2.2"/>
    </svg>`,
  },
  {
    name: "松任谷由実",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="松任谷由実のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q52 60 55 148 L67 150 L65 62 Z" fill="#2b2830"/>
      <path d="M98 42 Q108 60 105 148 L93 150 L95 62 Z" fill="#2b2830"/>
      <polygon points="58,72 63,74 60,140" fill="#3c3948"/>
      <polygon points="102,72 97,74 100,140" fill="#3c3948"/>
      <path d="M73 138 L71 172 M87 138 L89 172" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="168" width="18" height="15" rx="5" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="80" y="168" width="18" height="15" rx="5" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="66,74 94,74 100,140 60,140" fill="#7a52a8"/>
      <polygon points="66,74 79,74 72,128" fill="#9370c4"/>
      <path d="M60 128 L100 128" stroke="#5a3888" stroke-width="2.5"/>
      <path d="M74 78 Q80 84 86 78" stroke="#c8b8e0" stroke-width="1.4" fill="none"/>
      <path d="M64 80 L54 104" stroke="#7a52a8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="52" cy="107" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L108 100" stroke="#7a52a8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="110" cy="103" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 28 80 27 Q101 28 98 50 Q94 36 80 37 Q66 36 62 50 Z" fill="#2b2830"/>
      <path d="M63 46 Q71 40 80 41 Q89 40 97 46" stroke="#413c4a" stroke-width="2" fill="none"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M68 46 Q73 43 77 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M83 46 Q88 43 92 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="80" cy="59" rx="3.2" ry="3.8" fill="#8a3a5a"/>
    </svg>`,
  },
  {
    name: "Creepy Nuts",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Creepy Nuts（R-指定とDJ松永）の2人のイラスト">
      <ellipse cx="80" cy="188" rx="52" ry="6" fill="#dcdce3"/>
      <path d="M42 134 L40 172 M52 134 L54 172" stroke="#26242a" stroke-width="8"/>
      <rect x="33" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <rect x="47" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <polygon points="34,76 60,76 58,136 36,136" fill="#33313a"/>
      <path d="M58 82 L57 100" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="56" cy="103" r="4.5" fill="#f2c9a4"/>
      <rect x="53" y="103" width="6" height="15" rx="3" fill="#3a3a40"/>
      <circle cx="56" cy="121" r="5" fill="#9aa0ad"/>
      <path d="M36 84 L30 90" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="29" cy="92" r="4.5" fill="#f2c9a4"/>
      <rect x="43" y="65" width="7" height="8" fill="#f2c9a4"/>
      <circle cx="46" cy="56" r="13" fill="#f2c9a4"/>
      <path d="M33 56 Q32 44 46 43 Q60 44 59 56 Q55 47 46 48 Q37 47 33 56 Z" fill="#2c2824"/>
      <path d="M33 52 Q32 40 46 40 Q60 40 59 52 L59 47 Q52 44 46 44 Q40 44 33 47 Z" fill="#c0392b"/>
      <path d="M32 49 L58 49" stroke="#8f2820" stroke-width="1.4"/>
      <path d="M46 44 L60 40 L60 45 L47 48 Z" fill="#a32d2d"/>
      <circle cx="41.5" cy="56" r="1.5" fill="#3b3630"/>
      <circle cx="50.5" cy="56" r="1.5" fill="#3b3630"/>
      <path d="M38 52 Q41 50 44 52 M48 52 Q51 50 54 52" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M43 62 Q46 63.5 49 62" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M106 134 L104 172 M118 134 L120 172" stroke="#1f1f24" stroke-width="8"/>
      <rect x="97" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <rect x="111" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <ellipse cx="112" cy="146" rx="24" ry="8" fill="#26242a"/>
      <ellipse cx="112" cy="144" rx="24" ry="8" fill="#3a3841"/>
      <circle cx="112" cy="144" r="14" fill="#1d1b20"/>
      <circle cx="112" cy="144" r="5" fill="#565060"/>
      <circle cx="112" cy="144" r="1.6" fill="#c8ccd6"/>
      <path d="M112 144 L124 138" stroke="#9aa0ad" stroke-width="1.8" stroke-linecap="round"/>
      <polygon points="100,78 124,78 122,132 102,132" fill="#2c2c31"/>
      <polygon points="100,78 109,78 104,108" fill="#3a3a42"/>
      <path d="M122 82 L128 96" stroke="#2c2c31" stroke-width="7" stroke-linecap="round"/>
      <circle cx="129" cy="99" r="4.5" fill="#f2c9a4"/>
      <path d="M102 82 L96 130" stroke="#2c2c31" stroke-width="7" stroke-linecap="round"/>
      <circle cx="95" cy="132" r="4.5" fill="#f2c9a4"/>
      <rect x="108" y="66" width="7" height="8" fill="#f2c9a4"/>
      <circle cx="112" cy="57" r="13" fill="#f2c9a4"/>
      <path d="M99 58 Q98 43 112 42 Q126 43 125 58 Q121 46 112 47 Q103 46 99 58 Z" fill="#2e2a28"/>
      <path d="M99 52 Q97 60 101 64 L103 56 Z" fill="#2e2a28"/>
      <rect x="102" y="53" width="20" height="5.5" rx="2.5" fill="#1a1a1e"/>
      <path d="M102 54 L98 52 M122 54 L126 52" stroke="#1a1a1e" stroke-width="1.5"/>
      <path d="M103 50 Q107 48 110 50 M114 50 Q117 48 121 50" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M108 63 Q112 65 116 63" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "緑黄色社会",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="緑黄色社会（長屋晴子中心）の3人のイラスト">
      <ellipse cx="80" cy="188" rx="56" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M32 130 L30 168 M42 130 L44 168" stroke="#4a4a52" stroke-width="7"/>
        <rect x="23" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <rect x="37" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="26,80 48,80 46,132 28,132" fill="#4a8a5c"/>
        <path d="M38 100 L18 86" stroke="#4a3320" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="40" cy="108" rx="11" ry="9" fill="#c08a4a"/>
        <ellipse cx="40" cy="108" rx="4.5" ry="3.5" fill="#7a4e26"/>
        <path d="M28 86 L24 92" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="23" cy="94" r="4" fill="#f2c9a4"/>
        <path d="M46 86 L46 98" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="45" cy="101" r="4" fill="#f2c9a4"/>
        <rect x="34" y="70" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="37" cy="62" r="11" fill="#f2c9a4"/>
        <path d="M26 62 Q25 50 37 49 Q49 50 48 62 Q47 55 43 57 Q45 52 40 54 Q41 50 36 53 Q37 50 32 54 Q28 55 26 62 Z" fill="#33302c"/>
        <circle cx="33" cy="62" r="1.4" fill="#3b3630"/>
        <circle cx="41" cy="62" r="1.4" fill="#3b3630"/>
        <path d="M34 67 Q37 69 40 67" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M118 130 L116 168 M128 130 L130 168" stroke="#4a4a52" stroke-width="7"/>
        <rect x="109" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <rect x="123" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="112,80 134,80 132,132 114,132" fill="#4a8a5c"/>
        <rect x="106" y="98" width="30" height="11" rx="2" fill="#2c2c30"/>
        <path d="M110 98 L110 106 M115 98 L115 106 M120 98 L120 106 M125 98 L125 106 M130 98 L130 106" stroke="#f0ece1" stroke-width="2.6"/>
        <path d="M112 86 L108 96" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <path d="M134 86 L136 96" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <rect x="120" y="70" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="123" cy="62" r="11" fill="#f2c9a4"/>
        <path d="M112 62 Q111 50 123 49 Q135 50 134 62 Q131 53 123 54 Q115 53 112 62 Z" fill="#4a3628"/>
        <polygon points="116,53 123,51 118,58" fill="#5c4530"/>
        <circle cx="119" cy="62" r="1.4" fill="#3b3630"/>
        <circle cx="127" cy="62" r="1.4" fill="#3b3630"/>
        <ellipse cx="123" cy="67.5" rx="2" ry="2.4" fill="#8a4a44"/>
      </g>
      <g>
        <path d="M74 132 L72 172 M86 132 L88 172" stroke="#3d8a54" stroke-width="9"/>
        <rect x="64" y="170" width="17" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
        <rect x="81" y="170" width="17" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
        <polygon points="64,70 96,70 94,132 66,132" fill="#4a9e60"/>
        <polygon points="64,70 72,70 68,124" fill="#66b878"/>
        <path d="M72 74 Q80 80 88 74" stroke="#c8e0cc" stroke-width="1.4" fill="none"/>
        <path d="M65 76 L52 92" stroke="#4a9e60" stroke-width="9" stroke-linecap="round"/>
        <circle cx="50" cy="95" r="4.5" fill="#f2c9a4"/>
        <path d="M95 76 L104 60" stroke="#4a9e60" stroke-width="9" stroke-linecap="round"/>
        <circle cx="106" cy="56" r="4.5" fill="#f2c9a4"/>
        <rect x="102" y="42" width="5.5" height="14" rx="2.5" fill="#3a3a40" transform="rotate(12 105 49)"/>
        <circle cx="103" cy="40" r="5" fill="#9aa0ad"/>
        <rect x="76" y="58" width="8" height="8" fill="#f2c9a4"/>
        <circle cx="80" cy="47" r="15" fill="#f2c9a4"/>
        <path d="M65 48 Q62 27 80 26 Q98 27 95 48 Q92 34 80 34 Q68 34 65 48 Z" fill="#33302c"/>
        <path d="M65 40 Q65 32 72 33 Q76 30 80 33 Q84 30 88 33 Q95 32 95 40 Q90 36 80 37 Q70 36 65 40 Z" fill="#3d3934"/>
        <path d="M64 42 Q60 50 63 58 L66 48 Z" fill="#33302c"/>
        <circle cx="74" cy="48" r="1.6" fill="#3b3630"/>
        <circle cx="86" cy="48" r="1.6" fill="#3b3630"/>
        <path d="M70 43.5 Q74 41.5 77 43.5" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <path d="M83 43.5 Q86 41.5 90 43.5" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <ellipse cx="80" cy="55.5" rx="3" ry="3.8" fill="#8a3a44"/>
      </g>
    </svg>`,
  },
  {
    name: "玉置浩二",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="玉置浩二のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#26242a" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#1f1e22"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#1f1e22"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#26242a"/>
      <polygon points="72,74 88,74 84,132 76,132" fill="#3a3841"/>
      <polygon points="72,74 80,84 88,74" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M64 80 L62 108" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="62" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 78 L98 104" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="94" y="94" width="8" height="14" rx="4" fill="#3a3a40"/>
      <circle cx="98" cy="93" r="5.5" fill="#9aa0ad"/>
      <circle cx="98" cy="93" r="2.2" fill="#5a606b"/>
      <path d="M98 98 L98 172" stroke="#4a4a52" stroke-width="2.5"/>
      <ellipse cx="98" cy="172" rx="10" ry="3" fill="#3a3841"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 48 Q62 30 80 30 Q98 30 97 48 Q90 40 80 41 Q70 40 63 48 Z" fill="#2c2824"/>
      <path d="M63 44 Q71 39 80 40 Q89 39 97 44" stroke="#413b34" stroke-width="1.8" fill="none"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M74 59 Q80 63 86 59" stroke="#8a4a44" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "ちゃんみな",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="ちゃんみなのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 40 Q46 58 52 100 L48 140 L62 142 L64 60 Z" fill="#211f26"/>
      <path d="M100 40 Q114 58 108 100 L112 140 L98 142 L96 60 Z" fill="#211f26"/>
      <polygon points="54,90 60,92 55,138" fill="#6a3a9e"/>
      <polygon points="106,90 100,92 105,138" fill="#6a3a9e"/>
      <path d="M73 138 L71 172 M87 138 L89 172" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="168" width="18" height="15" rx="5" fill="#2a2830"/>
      <rect x="80" y="168" width="18" height="15" rx="5" fill="#2a2830"/>
      <polygon points="64,74 96,74 100,138 60,138" fill="#3a3540"/>
      <polygon points="64,74 78,74 71,126" fill="#4a4550"/>
      <path d="M60 126 L100 126" stroke="#26232c" stroke-width="2.5"/>
      <path d="M64 80 L52 100" stroke="#3a3540" stroke-width="8" stroke-linecap="round"/>
      <circle cx="80" cy="90" r="5" fill="#7a4aa8"/>
      <path d="M96 80 L108 100" stroke="#3a3540" stroke-width="8" stroke-linecap="round"/>
      <circle cx="110" cy="103" r="5" fill="#f2c9a4"/>
      <rect x="106" y="90" width="6" height="15" rx="3" fill="#3a3a40"/>
      <circle cx="80" cy="84" r="4.5" fill="#8f4ac0"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 28 80 27 Q101 28 98 50 L98 42 Q98 38 92 38 L68 38 Q62 38 62 42 Z" fill="#211f26"/>
      <path d="M64 40 L96 40" stroke="#6a3a9e" stroke-width="2.5"/>
      <path d="M66 40 L66 47 M72 40 L72 47 M78 40 L78 47 M84 40 L84 47 M90 40 L90 47 M96 40 L96 47" stroke="#211f26" stroke-width="2"/>
      <path d="M68 46 L76 46 M84 46 L92 46" stroke="#3b3630" stroke-width="2"/>
      <circle cx="73" cy="52" r="1.9" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.9" fill="#3b3630"/>
      <path d="M70 49 L76 49 M84 49 L90 49" stroke="#3b3630" stroke-width="0.8"/>
      <path d="M76 59 Q80 62 84 59 Q80 57.5 76 59 Z" fill="#a3455e"/>
    </svg>`,
  },
  {
    name: "大野雄大（Da-iCE）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="大野雄大（Da-iCE）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#2c3a4a" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#1f1e22"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#1f1e22"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#33404f"/>
      <polygon points="72,74 88,74 84,132 76,132" fill="#41505f"/>
      <polygon points="72,74 80,84 88,74" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M76 78 L80 96 L84 78" stroke="#2c3a4a" stroke-width="3" fill="none"/>
      <path d="M63 82 L53 106" stroke="#33404f" stroke-width="9" stroke-linecap="round"/>
      <circle cx="52" cy="110" r="5" fill="#f2c9a4"/>
      <path d="M97 80 L110 58" stroke="#33404f" stroke-width="9" stroke-linecap="round"/>
      <circle cx="112" cy="54" r="5" fill="#f2c9a4"/>
      <rect x="108" y="36" width="6" height="16" rx="3" fill="#3a3a40" transform="rotate(16 111 44)"/>
      <circle cx="109" cy="34" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 48 Q62 31 80 31 Q98 31 97 48 Q90 42 80 43 Q70 42 63 48 Z" fill="#2b2824"/>
      <polygon points="68,36 78,33 71,42" fill="#3d3934"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M75 59 Q80 62 85 59" stroke="#8a4a44" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "HY",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="HY（仲宗根泉・キーボードボーカル）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 42 Q50 60 54 138 L66 140 L64 62 Z" fill="#2e2a26"/>
      <path d="M98 42 Q110 60 106 138 L94 140 L96 62 Z" fill="#2e2a26"/>
      <path d="M73 134 L71 158 M87 134 L89 158" stroke="#e07a2c" stroke-width="9"/>
      <polygon points="64,74 96,74 100,136 60,136" fill="#e8862e"/>
      <polygon points="64,74 78,74 71,124" fill="#f0a052"/>
      <path d="M60 124 L100 124" stroke="#b85e18" stroke-width="2.5"/>
      <rect x="40" y="150" width="80" height="12" rx="2" fill="#2c2c30"/>
      <rect x="40" y="150" width="80" height="4" fill="#3a3a40"/>
      <path d="M46 154 L46 162 M52 154 L52 162 M58 154 L58 162 M64 154 L64 162 M70 154 L70 162 M76 154 L76 162 M82 154 L82 162 M88 154 L88 162 M94 154 L94 162 M100 154 L100 162 M106 154 L106 162 M112 154 L112 162" stroke="#f0ece1" stroke-width="2.4"/>
      <rect x="49" y="150" width="3" height="6" fill="#1f1e22"/>
      <rect x="61" y="150" width="3" height="6" fill="#1f1e22"/>
      <rect x="79" y="150" width="3" height="6" fill="#1f1e22"/>
      <rect x="91" y="150" width="3" height="6" fill="#1f1e22"/>
      <rect x="103" y="150" width="3" height="6" fill="#1f1e22"/>
      <path d="M64 80 L54 140" stroke="#e8862e" stroke-width="8" stroke-linecap="round"/>
      <circle cx="53" cy="148" r="4.5" fill="#f2c9a4"/>
      <path d="M96 80 L106 140" stroke="#e8862e" stroke-width="8" stroke-linecap="round"/>
      <circle cx="107" cy="148" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 28 80 27 Q101 28 98 50 Q94 36 80 37 Q66 36 62 50 Z" fill="#2e2a26"/>
      <path d="M63 46 Q71 40 80 41 Q89 40 97 46" stroke="#413a34" stroke-width="1.8" fill="none"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="57" rx="2.6" ry="1.6" fill="#f0aeae"/>
      <ellipse cx="92" cy="57" rx="2.6" ry="1.6" fill="#f0aeae"/>
      <path d="M76 58 Q80 61 84 58" stroke="#b0566a" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "DREAMS COME TRUE",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="DREAMS COME TRUE（吉田美和）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M58 38 Q42 54 48 96 Q44 120 56 140 L68 138 L62 58 Z" fill="#2b2622"/>
      <path d="M102 38 Q118 54 112 96 Q116 120 104 140 L92 138 L98 58 Z" fill="#2b2622"/>
      <path d="M52 72 Q44 90 52 110" stroke="#3d372f" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M108 72 Q116 90 108 110" stroke="#3d372f" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M73 138 L71 172 M87 138 L89 172" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="168" width="18" height="15" rx="5" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="80" y="168" width="18" height="15" rx="5" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="64,74 96,74 102,138 58,138" fill="#efe9dc" stroke="#bcb5a4" stroke-width="1.2"/>
      <polygon points="64,74 78,74 71,126" fill="#e2dccb"/>
      <path d="M64 126 L100 126" stroke="#c4bca8" stroke-width="2"/>
      <path d="M70 84 L68 90 L71 90 L69.5 96" stroke="#d8404a" stroke-width="2" fill="none"/>
      <circle cx="70" cy="98" r="1.8" fill="#d8404a"/>
      <path d="M86 94 L84 100 L87 100 L85.5 106" stroke="#3d8ac0" stroke-width="2" fill="none"/>
      <circle cx="86" cy="108" r="1.8" fill="#3d8ac0"/>
      <path d="M78 108 L76 114 L79 114" stroke="#e0a52c" stroke-width="2" fill="none"/>
      <circle cx="78" cy="116" r="1.8" fill="#e0a52c"/>
      <path d="M92 82 L90 88 L93 88" stroke="#4a9e60" stroke-width="2" fill="none"/>
      <circle cx="92" cy="90" r="1.8" fill="#4a9e60"/>
      <path d="M64 80 L52 100" stroke="#efe9dc" stroke-width="8" stroke-linecap="round"/>
      <circle cx="50" cy="103" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L108 60" stroke="#efe9dc" stroke-width="8" stroke-linecap="round"/>
      <circle cx="110" cy="56" r="5" fill="#f2c9a4"/>
      <rect x="106" y="38" width="6" height="16" rx="3" fill="#3a3a40" transform="rotate(14 109 46)"/>
      <circle cx="107" cy="36" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M60 52 Q54 26 80 25 Q106 26 100 52 Q95 34 80 34 Q65 34 60 52 Z" fill="#2b2622"/>
      <path d="M62 40 Q71 33 80 34 Q89 33 98 40" stroke="#3d372f" stroke-width="2" fill="none"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="57" rx="2.6" ry="1.6" fill="#f0aeae"/>
      <ellipse cx="92" cy="57" rx="2.6" ry="1.6" fill="#f0aeae"/>
      <path d="M75 58 Q80 62 85 58" stroke="#b0566a" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
];
