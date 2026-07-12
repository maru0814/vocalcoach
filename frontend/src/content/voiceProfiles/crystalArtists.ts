import type { ProfileArtist } from "./types";

// Crystalタイプの有名人イラスト（docs/62 §10-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。
// 並び順は女男の完全交互（女→男）。9組。

export const CRYSTAL_ARTISTS: ProfileArtist[] = [
  {
    name: "ずっと真夜中でいいのに。",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="ずっと真夜中でいいのに。（ACAね）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#3a352e" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="62,74 98,74 95,136 65,136" fill="#d9a637"/>
      <polygon points="74,74 86,74 84,110 76,110" fill="#e8bd5c"/>
      <path d="M64 88 L96 88 M65 108 L95 108" stroke="#b8862a" stroke-width="1.6"/>
      <circle cx="80" cy="98" r="2.2" fill="#f3e0a8"/>
      <path d="M65 80 L54 106" stroke="#d9a637" stroke-width="9" stroke-linecap="round"/>
      <circle cx="52" cy="110" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L106 106" stroke="#d9a637" stroke-width="9" stroke-linecap="round"/>
      <circle cx="108" cy="110" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M64 40 L61 22 L70 30 L80 20 L90 30 L99 22 L96 40 Q80 33 64 40 Z" fill="#2e2b30"/>
      <path d="M60 42 Q57 36 63 32 L67 42 Z" stroke="#2e2b30" stroke-width="6" fill="#2e2b30"/>
      <path d="M100 42 Q103 36 97 32 L93 42 Z" stroke="#2e2b30" stroke-width="6" fill="#2e2b30"/>
      <path d="M62 30 Q80 22 98 30 L98 26 Q80 18 62 26 Z" fill="#3a3640"/>
      <path d="M66 40 Q68 34 74 32 M94 40 Q92 34 86 32" stroke="#4a4650" stroke-width="1.4" fill="none"/>
      <path d="M64 46 Q80 40 96 46 L96 54 Q80 49 64 54 Z" fill="#2e2b30"/>
      <path d="M66 55 Q73 53 79 55" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M81 55 Q87 53 94 55" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="70" cy="60" rx="2.6" ry="1.6" fill="#f0b0a0"/>
      <ellipse cx="90" cy="60" rx="2.6" ry="1.6" fill="#f0b0a0"/>
      <ellipse cx="80" cy="61" rx="3" ry="3.6" fill="#c05a70"/>
    </svg>`,
  },
  {
    name: "Official髭男dism",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Official髭男dism（藤原聡・Pretender仕様）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <rect x="18" y="30" width="26" height="16" rx="2" fill="#e05a8a"/>
      <rect x="20" y="32" width="22" height="12" rx="1" fill="#f090b8"/>
      <path d="M24 36 L38 36 M24 40 L34 40" stroke="#fce0ec" stroke-width="1.4"/>
      <rect x="120" y="24" width="22" height="14" rx="2" fill="#3a7fc0"/>
      <rect x="122" y="26" width="18" height="10" rx="1" fill="#6ab0e8"/>
      <path d="M126 30 L136 30 M126 33 L134 33" stroke="#d6ecfb" stroke-width="1.3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#26303f" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#26242a" stroke="#4a4650" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#26242a" stroke="#4a4650" stroke-width="1"/>
      <polygon points="62,74 98,74 95,134 65,134" fill="#2e3a52"/>
      <polygon points="62,74 79,74 72,120" fill="#37455f"/>
      <polygon points="80,74 98,74 88,120" fill="#26304a"/>
      <path d="M74 74 L80 96 L86 74" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M78 88 L82 88" stroke="#c9a24a" stroke-width="2"/>
      <path d="M65 80 L57 100" stroke="#2e3a52" stroke-width="9" stroke-linecap="round"/>
      <circle cx="56" cy="103" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L92 104" stroke="#2e3a52" stroke-width="9" stroke-linecap="round"/>
      <circle cx="91" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="98" y="112" width="6" height="30" rx="3" fill="#3a3a40"/>
      <ellipse cx="101" cy="112" rx="5.5" ry="7" fill="#9aa0ad"/>
      <path d="M99 108 Q101 104 103 108" stroke="#c8ccd6" stroke-width="1.2" fill="none"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 48 Q58 28 80 27 Q102 28 98 48 Q96 36 88 36 Q84 40 80 39 Q76 40 72 36 Q64 36 62 48 Z" fill="#26232a"/>
      <path d="M63 40 Q70 32 80 33 Q90 32 97 40 Q88 30 80 31 Q72 30 63 40 Z" fill="#33303a"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="59" rx="3.2" ry="3.8" fill="#8a4a44"/>
    </svg>`,
  },
  {
    name: "松田聖子",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="松田聖子のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 44 Q44 54 46 74 L58 72 L62 58 Z" fill="#6b4b33"/>
      <path d="M100 44 Q116 54 114 74 L102 72 L98 58 Z" fill="#6b4b33"/>
      <path d="M73 136 L71 168 M87 136 L89 168" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="164" width="18" height="18" rx="6" fill="#f5eef2" stroke="#c9bcc4" stroke-width="1.2"/>
      <rect x="80" y="164" width="18" height="18" rx="6" fill="#f5eef2" stroke="#c9bcc4" stroke-width="1.2"/>
      <polygon points="66,74 94,74 100,120 60,120" fill="#f5b8ce"/>
      <polygon points="66,74 79,74 72,112" fill="#fbcfe0"/>
      <path d="M56 120 Q80 116 104 120 L108 134 Q80 129 52 134 Z" fill="#f5b8ce"/>
      <path d="M52 134 Q80 129 108 134 L112 150 Q80 145 48 150 Z" fill="#f0a8c2"/>
      <path d="M60 124 L100 124" stroke="#e88bb0" stroke-width="1.8"/>
      <path d="M66 88 Q73 82 80 88 Q87 82 94 88" stroke="#fbcfe0" stroke-width="2" fill="none"/>
      <circle cx="80" cy="98" r="3" fill="#fff" stroke="#e88bb0" stroke-width="1"/>
      <path d="M65 80 L54 104" stroke="#f5b8ce" stroke-width="8" stroke-linecap="round"/>
      <circle cx="52" cy="107" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L106 104" stroke="#f5b8ce" stroke-width="8" stroke-linecap="round"/>
      <circle cx="108" cy="107" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 30 80 29 Q101 30 98 50 Q94 37 80 38 Q66 37 62 50 Z" fill="#5c4030"/>
      <path d="M64 40 Q72 34 80 35 Q88 34 96 40 Q88 32 80 33 Q72 32 64 40 Z" fill="#6b4b3a"/>
      <polygon points="68,34 78,31 71,40" fill="#7a5a44"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 43 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 43 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="70" cy="57" rx="2.6" ry="1.6" fill="#f5a0b4"/>
      <ellipse cx="90" cy="57" rx="2.6" ry="1.6" fill="#f5a0b4"/>
      <path d="M76 59 Q80 63 84 59" stroke="#d8607e" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "ONE OK ROCK",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="ONE OK ROCK（Taka）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#1f1f24" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#26242a" stroke="#4a4650" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#26242a" stroke="#4a4650" stroke-width="1"/>
      <polygon points="64,74 96,74 94,134 66,134" fill="#26242a"/>
      <path d="M72 74 Q80 82 88 74 L88 108 L72 108 Z" fill="#e8c090"/>
      <rect x="79" y="100" width="2.5" height="16" rx="1" fill="#9aa0ad"/>
      <rect x="76" y="114" width="8" height="6" rx="1.5" fill="#8a909d"/>
      <path d="M78 116 L82 116" stroke="#6a707d" stroke-width="1"/>
      <path d="M95 80 L112 48" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="114" cy="44" r="5.5" fill="#e8c090"/>
      <rect x="110" y="26" width="6" height="18" rx="3" fill="#3a3a40" transform="rotate(16 113 34)"/>
      <circle cx="110" cy="24" r="5.5" fill="#9aa0ad"/>
      <circle cx="108" cy="20" r="1.5" fill="#c8ccd6"/>
      <path d="M65 80 L58 102" stroke="#26242a" stroke-width="9" stroke-linecap="round"/>
      <circle cx="57" cy="105" r="5" fill="#e8c090"/>
      <rect x="76" y="62" width="8" height="8" fill="#e8c090"/>
      <circle cx="80" cy="50" r="16" fill="#e8c090"/>
      <path d="M63 48 Q60 30 80 30 Q100 30 97 48 Q94 40 80 41 Q66 40 63 48 Z" fill="#221f24"/>
      <polygon points="68,34 77,31 72,41" fill="#332f36"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="59" rx="3.4" ry="4.2" fill="#7d3b3b"/>
    </svg>`,
  },
  {
    name: "西野カナ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="西野カナのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 44 Q46 62 50 132 Q54 140 60 132 Q56 96 66 66 Z" fill="#7a5636"/>
      <path d="M100 44 Q114 62 110 132 Q106 140 100 132 Q104 96 94 66 Z" fill="#7a5636"/>
      <path d="M50 128 Q46 136 52 138 Q56 132 50 128 Z" fill="#8a6644"/>
      <path d="M110 128 Q114 136 108 138 Q104 132 110 128 Z" fill="#8a6644"/>
      <path d="M73 136 L71 168 M87 136 L89 168" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="164" width="18" height="18" rx="6" fill="#f6eef1" stroke="#cabcc2" stroke-width="1.2"/>
      <rect x="80" y="164" width="18" height="18" rx="6" fill="#f6eef1" stroke="#cabcc2" stroke-width="1.2"/>
      <polygon points="66,74 94,74 100,124 60,124" fill="#f4b0c8"/>
      <polygon points="66,74 79,74 72,114" fill="#facfe0"/>
      <path d="M70 74 Q80 80 90 74 L88 82 Q80 88 72 82 Z" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1"/>
      <circle cx="80" cy="76" r="3" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M78 76 L74 72 M82 76 L86 72" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M65 80 L54 104" stroke="#f4b0c8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="52" cy="107" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L106 104" stroke="#f4b0c8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="108" cy="107" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 30 80 29 Q101 30 98 50 Q94 37 80 38 Q66 37 62 50 Z" fill="#7a5636"/>
      <path d="M64 42 Q72 36 80 37 Q88 36 96 42 Q88 34 80 35 Q72 34 64 42 Z" fill="#8a6644"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M68 48 L71 47 L74 48 M86 48 L89 47 L92 48" stroke="#3b3630" stroke-width="1.1" fill="none" stroke-linecap="round"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="70" cy="57" rx="2.6" ry="1.6" fill="#f5a0b4"/>
      <ellipse cx="90" cy="57" rx="2.6" ry="1.6" fill="#f5a0b4"/>
      <ellipse cx="80" cy="60" rx="3" ry="3.6" fill="#c8607a"/>
    </svg>`,
  },
  {
    name: "スキマスイッチ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="スキマスイッチ（大橋と常田）の2人のイラスト">
      <ellipse cx="80" cy="188" rx="52" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M42 134 L40 172 M52 134 L54 172" stroke="#3a4658" stroke-width="8"/>
        <rect x="33" y="170" width="16" height="8" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
        <rect x="47" y="170" width="16" height="8" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
        <polygon points="34,76 60,76 58,136 36,136" fill="#4a5468"/>
        <path d="M48 102 L22 84" stroke="#6b4b33" stroke-width="4.5" stroke-linecap="round"/>
        <rect x="14" y="76" width="9" height="9" rx="2" fill="#4a3320"/>
        <ellipse cx="50" cy="112" rx="15" ry="12" fill="#d9a860"/>
        <ellipse cx="50" cy="112" rx="6" ry="5" fill="#8a6030"/>
        <path d="M48 106 L24 88" stroke="#e8d9c0" stroke-width="0.8"/>
        <path d="M40 100 L60 124" stroke="#b8863a" stroke-width="3"/>
        <path d="M58 84 L57 100" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
        <circle cx="56" cy="103" r="4.5" fill="#f2c9a4"/>
        <path d="M36 84 L30 88" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
        <circle cx="29" cy="89" r="4.5" fill="#f2c9a4"/>
        <rect x="43" y="65" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="46" cy="56" r="13" fill="#f2c9a4"/>
        <path d="M33 54 Q32 40 46 39 Q60 40 59 54 Q55 45 46 46 Q37 45 33 54 Z" fill="#3a2e26"/>
        <polygon points="38,42 46,39 42,48" fill="#4a3a2e"/>
        <circle cx="41.5" cy="56" r="1.5" fill="#3b3630"/>
        <circle cx="50.5" cy="56" r="1.5" fill="#3b3630"/>
        <path d="M38 51 Q41 49 44 51 M48 51 Q51 49 54 51" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <path d="M42 62 Q46 64 50 62" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M106 134 L104 172 M118 134 L120 172" stroke="#2e3640" stroke-width="8"/>
        <rect x="97" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <rect x="111" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="100,76 124,76 122,136 102,136" fill="#3a4048"/>
        <rect x="94" y="106" width="38" height="12" rx="2" fill="#2c2c30"/>
        <path d="M98 106 L98 116 M104 106 L104 116 M110 106 L110 116 M116 106 L116 116 M122 106 L122 116 M128 106 L128 116" stroke="#f2f0ea" stroke-width="2.6"/>
        <path d="M101 82 L96 104" stroke="#f2c9a4" stroke-width="8" stroke-linecap="round"/>
        <path d="M123 82 L128 104" stroke="#f2c9a4" stroke-width="8" stroke-linecap="round"/>
        <rect x="108" y="66" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="112" cy="55" r="14" fill="#f2c9a4"/>
        <circle cx="100" cy="46" r="7" fill="#2e2a26"/>
        <circle cx="108" cy="40" r="8" fill="#2e2a26"/>
        <circle cx="118" cy="40" r="8" fill="#2e2a26"/>
        <circle cx="126" cy="47" r="7" fill="#2e2a26"/>
        <circle cx="98" cy="54" r="6" fill="#2e2a26"/>
        <circle cx="126" cy="55" r="6" fill="#2e2a26"/>
        <path d="M99 48 Q108 40 118 41 Q127 42 125 50 Q116 44 108 45 Q100 44 99 48 Z" fill="#2e2a26"/>
        <circle cx="105" cy="55" r="4.5" fill="none" stroke="#3a3640" stroke-width="1.6"/>
        <circle cx="119" cy="55" r="4.5" fill="none" stroke="#3a3640" stroke-width="1.6"/>
        <path d="M109.5 55 L114.5 55" stroke="#3a3640" stroke-width="1.4"/>
        <circle cx="105" cy="55" r="1.5" fill="#3b3630"/>
        <circle cx="119" cy="55" r="1.5" fill="#3b3630"/>
        <path d="M107 62 Q112 64 117 62" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
    </svg>`,
  },
  {
    name: "チャットモンチー",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="チャットモンチー（橋本と福岡）の2人のイラスト">
      <ellipse cx="80" cy="188" rx="52" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M42 134 L40 172 M52 134 L54 172" stroke="#3a3540" stroke-width="8"/>
        <rect x="33" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <rect x="47" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="34,76 60,76 58,136 36,136" fill="#c0405a"/>
        <path d="M48 102 L22 84" stroke="#6b6b74" stroke-width="4.5" stroke-linecap="round"/>
        <rect x="14" y="76" width="9" height="9" rx="2" fill="#3a3a44"/>
        <path d="M44 100 L58 124" stroke="#7a7a84" stroke-width="3"/>
        <ellipse cx="50" cy="112" rx="14" ry="11" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1.2"/>
        <ellipse cx="50" cy="112" rx="4.5" ry="3.5" fill="#d9d3c5"/>
        <polygon points="42,104 52,102 46,116" fill="#e6e0d2"/>
        <path d="M58 84 L57 100" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
        <circle cx="56" cy="103" r="4.5" fill="#f2c9a4"/>
        <path d="M36 84 L30 88" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
        <circle cx="29" cy="89" r="4.5" fill="#f2c9a4"/>
        <rect x="43" y="65" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="46" cy="56" r="13" fill="#f2c9a4"/>
        <path d="M33 56 Q31 41 46 40 Q61 41 59 56 L57 66 Q57 48 46 48 Q35 48 35 66 L33 56 Z" fill="#241f26"/>
        <polygon points="38,42 46,40 42,49" fill="#3a3240"/>
        <circle cx="41.5" cy="55" r="1.5" fill="#3b3630"/>
        <circle cx="50.5" cy="55" r="1.5" fill="#3b3630"/>
        <path d="M38 50 Q41 48 44 50 M48 50 Q51 48 54 50" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <path d="M42 61 Q46 63 50 61" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M106 134 L104 172 M118 134 L120 172" stroke="#3a3540" stroke-width="8"/>
        <rect x="97" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <rect x="111" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <path d="M100 66 Q95 82 98 132 L103 134 L102 76 Z" fill="#4a3628"/>
        <path d="M124 66 Q129 82 126 132 L121 134 L122 76 Z" fill="#4a3628"/>
        <polygon points="100,76 124,76 122,136 102,136" fill="#5a7ba0"/>
        <path d="M112 100 L134 84" stroke="#3a2e24" stroke-width="5" stroke-linecap="round"/>
        <rect x="130" y="78" width="9" height="10" rx="2" fill="#2c2420"/>
        <polygon points="104,110 118,110 116,134 106,134" fill="#3a2e24"/>
        <path d="M107 114 L107 130 M112 114 L112 130" stroke="#5a4a3a" stroke-width="1.6"/>
        <path d="M101 82 L96 104" stroke="#5a7ba0" stroke-width="8" stroke-linecap="round"/>
        <circle cx="95" cy="107" r="4.5" fill="#f2c9a4"/>
        <path d="M123 82 L129 100" stroke="#5a7ba0" stroke-width="8" stroke-linecap="round"/>
        <circle cx="130" cy="103" r="4.5" fill="#f2c9a4"/>
        <rect x="108" y="66" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="112" cy="56" r="13" fill="#f2c9a4"/>
        <path d="M98 58 Q96 41 112 40 Q128 41 126 58 Q123 46 112 47 Q101 46 98 58 Z" fill="#4a3628"/>
        <polygon points="103,44 112,41 107,50" fill="#5a4432"/>
        <circle cx="107" cy="56" r="1.5" fill="#3b3630"/>
        <circle cx="117" cy="56" r="1.5" fill="#3b3630"/>
        <path d="M103 51 Q107 49 110 51 M114 51 Q117 49 121 51" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <ellipse cx="112" cy="62" rx="2.6" ry="3.2" fill="#8a4a44"/>
      </g>
    </svg>`,
  },
  {
    name: "クリープハイプ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="クリープハイプ（尾崎世界観）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#3a3540" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#26242a" stroke="#4a4650" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#26242a" stroke="#4a4650" stroke-width="1"/>
      <polygon points="62,74 98,74 95,134 65,134" fill="#5a6a80"/>
      <polygon points="62,74 79,74 72,118" fill="#6a7890"/>
      <path d="M66 78 L94 78 M64 96 L96 96 M65 114 L95 114" stroke="#48576b" stroke-width="1.4"/>
      <path d="M66 78 L92 112" stroke="#7a4a3a" stroke-width="4"/>
      <path d="M92 108 L64 86" stroke="#a35a3a" stroke-width="5" stroke-linecap="round"/>
      <rect x="55" y="78" width="9" height="9" rx="2" fill="#5a3428"/>
      <ellipse cx="94" cy="116" rx="16" ry="13" fill="#b8503a"/>
      <ellipse cx="94" cy="116" rx="6.5" ry="5.5" fill="#7a3020"/>
      <path d="M92 110 L66 88" stroke="#e0c0a0" stroke-width="0.8"/>
      <path d="M65 80 L60 88" stroke="#5a6a80" stroke-width="9" stroke-linecap="round"/>
      <circle cx="60" cy="90" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L97 104" stroke="#5a6a80" stroke-width="9" stroke-linecap="round"/>
      <circle cx="96" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q58 29 80 28 Q102 29 98 50 Q96 36 90 36 L86 42 L80 37 L74 42 L70 36 Q64 36 62 50 Z" fill="#221f24"/>
      <polygon points="67,34 78,30 71,42" fill="#332f36"/>
      <path d="M84 33 Q92 31 96 38" stroke="#332f36" stroke-width="3" fill="none" stroke-linecap="round"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M76 59 Q80 61 84 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "華原朋美",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="華原朋美のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 44 Q46 62 50 130 Q54 138 60 130 Q56 92 66 66 Z" fill="#7a5636"/>
      <path d="M100 44 Q114 62 110 130 Q106 138 100 130 Q104 92 94 66 Z" fill="#7a5636"/>
      <path d="M54 92 Q58 100 54 108 M106 92 Q102 100 106 108" stroke="#8a6644" stroke-width="1.4" fill="none"/>
      <path d="M73 138 L71 168 M87 138 L89 168" stroke="#f2c9a4" stroke-width="8"/>
      <polygon points="60,74 100,74 108,150 52,150" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
      <polygon points="60,74 74,74 66,148 54,148" fill="#e2dccb"/>
      <path d="M62 96 Q80 102 98 96 M60 118 Q80 124 100 118 M56 140 Q80 146 104 140" stroke="#cfc7b2" stroke-width="1.6" fill="none"/>
      <path d="M70 74 Q80 82 90 74 L88 84 Q80 90 72 84 Z" fill="#e6dfce"/>
      <path d="M66 80 L54 104" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
      <path d="M54 104 Q60 108 62 102" stroke="#f0ece1" stroke-width="9" stroke-linecap="round" fill="none"/>
      <circle cx="61" cy="106" r="5" fill="#f2c9a4"/>
      <path d="M94 80 L106 104" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
      <path d="M106 104 Q100 108 98 102" stroke="#f0ece1" stroke-width="9" stroke-linecap="round" fill="none"/>
      <circle cx="99" cy="106" r="5" fill="#f2c9a4"/>
      <rect x="76" y="66" width="8" height="14" rx="3" fill="#3a3a40" transform="rotate(-4 80 72)"/>
      <ellipse cx="80" cy="64" rx="6" ry="7" fill="#9aa0ad"/>
      <path d="M77 61 Q80 57 83 61" stroke="#c8ccd6" stroke-width="1.2" fill="none"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 30 80 29 Q101 30 98 50 Q94 37 80 38 Q66 37 62 50 Z" fill="#7a5636"/>
      <path d="M63 44 Q72 37 80 38 Q88 37 97 44 Q88 34 80 35 Q72 34 63 44 Z" fill="#8a6644"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="70" cy="57" rx="2.6" ry="1.6" fill="#f0aebe"/>
      <ellipse cx="90" cy="57" rx="2.6" ry="1.6" fill="#f0aebe"/>
      <path d="M76 58 Q80 62 84 58 Q80 60 76 58 Z" fill="#c05a70"/>
    </svg>`,
  },
];
