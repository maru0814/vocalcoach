import type { ProfileArtist } from "./types";

// Sweet（whisper）タイプの有名人イラスト（docs/62 §12-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 木漏れ日のやわらかく明るいトーン。白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。
// 並び順は「女男男の繰り返し」で同性3連続を回避（11組）。

export const WHISPER_ARTISTS: ProfileArtist[] = [
  {
    name: "幾田りら",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="幾田りらのイラスト">
      <ellipse cx="80" cy="188" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 44 Q54 62 58 122 L68 124 L66 66 Z" fill="#8a6440"/>
      <path d="M98 44 Q106 62 102 122 L92 124 L94 66 Z" fill="#8a6440"/>
      <path d="M72 132 L69 168 M88 132 L91 168" stroke="#c98a4a" stroke-width="12"/>
      <path d="M69 168 L72 132 M91 168 L88 132 M73 134 L71 168 M78 134 L77 168 M83 134 L84 168" stroke="#b57a3c" stroke-width="1.2"/>
      <rect x="60" y="166" width="19" height="15" rx="4" fill="#5a4636"/>
      <rect x="81" y="166" width="19" height="15" rx="4" fill="#5a4636"/>
      <polygon points="62,80 98,80 100,134 60,134" fill="#f0e4c4"/>
      <polygon points="62,80 74,80 68,124" fill="#f6efd6"/>
      <path d="M62 92 Q80 98 98 92 M63 106 Q80 112 97 106 M64 120 Q80 126 96 120" stroke="#dccca0" stroke-width="1.5" fill="none"/>
      <circle cx="80" cy="76" r="2.6" fill="#e0be4a"/>
      <path d="M77 76 Q80 84 83 76" stroke="#e0be4a" stroke-width="1.4" fill="none"/>
      <path d="M64 84 L54 108" stroke="#f0e4c4" stroke-width="10" stroke-linecap="round"/>
      <circle cx="52" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 84 L106 108" stroke="#f0e4c4" stroke-width="10" stroke-linecap="round"/>
      <circle cx="108" cy="112" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 30 80 29 Q101 30 98 52 Q94 40 80 41 Q66 40 62 52 Z" fill="#8a6440"/>
      <path d="M62 52 Q60 62 63 68 L67 58 Z M98 52 Q100 62 97 68 L93 58 Z" fill="#8a6440"/>
      <polygon points="68,34 78,31 72,41" fill="#a37c50"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <path d="M76 58 Q80 61 84 58" stroke="#c07a70" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "井口理（King Gnu）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="井口理（King Gnu）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#3a3d4a" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="61,74 99,74 96,136 64,136" fill="#7d8aa0"/>
      <polygon points="61,74 73,74 67,124" fill="#8f9bb0"/>
      <path d="M68 76 Q72 82 80 82 Q88 82 92 76" stroke="#5c687e" stroke-width="3" fill="none"/>
      <path d="M76 84 L76 108 M84 84 L84 108" stroke="#5c687e" stroke-width="1.6"/>
      <circle cx="76" cy="94" r="1.4" fill="#4a566c"/>
      <circle cx="84" cy="94" r="1.4" fill="#4a566c"/>
      <path d="M64 82 L56 108" stroke="#7d8aa0" stroke-width="9" stroke-linecap="round"/>
      <circle cx="55" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M96 82 L104 108" stroke="#7d8aa0" stroke-width="9" stroke-linecap="round"/>
      <circle cx="105" cy="112" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q58 28 80 27 Q102 28 98 52 Q99 40 94 40 Q90 35 80 37 Q70 35 66 40 Q61 40 62 52 Z" fill="#2b2830"/>
      <path d="M62 52 Q59 46 63 42 L66 50 Z M98 52 Q101 46 97 42 L94 50 Z" fill="#2b2830"/>
      <polygon points="67,35 77,32 71,42" fill="#403c46"/>
      <path d="M70 52 Q73 55 76 52" stroke="#3b3630" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="M84 52 Q87 55 90 52" stroke="#3b3630" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="M69 46 Q73 45 76 47" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 47 Q87 45 91 46" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M75 59 Q80 62 85 59" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "小田和正",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="小田和正のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#c9bfa8" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#d9cfb8" stroke="#b3a988" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#d9cfb8" stroke="#b3a988" stroke-width="1"/>
      <polygon points="62,74 98,74 96,134 64,134" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1.2"/>
      <polygon points="62,74 73,74 67,132" fill="#e6e1d3"/>
      <path d="M80 76 L80 132" stroke="#cfc7b4" stroke-width="1.4"/>
      <circle cx="80" cy="90" r="1.2" fill="#bcb5a4"/>
      <circle cx="80" cy="102" r="1.2" fill="#bcb5a4"/>
      <circle cx="80" cy="114" r="1.2" fill="#bcb5a4"/>
      <path d="M96 80 L102 100" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <path d="M102 100 Q98 108 92 106" stroke="#f4f1e9" stroke-width="9" fill="none" stroke-linecap="round"/>
      <circle cx="90" cy="104" r="4.5" fill="#f2c9a4"/>
      <rect x="86" y="76" width="6" height="30" rx="3" fill="#4a4650" transform="rotate(20 89 90)"/>
      <circle cx="95" cy="70" r="6" fill="#8f95a2"/>
      <circle cx="95" cy="70" r="3" fill="#c8ccd6"/>
      <path d="M64 80 L54 104" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <circle cx="52" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M64 48 Q62 33 80 32 Q98 33 96 48 Q92 39 80 40 Q68 39 64 48 Z" fill="#d8d5cf"/>
      <path d="M64 48 Q64 42 70 41 M96 48 Q96 42 90 41" stroke="#bcb5b0" stroke-width="1.4" fill="none"/>
      <path d="M64 48 Q62 34 80 33 Q98 34 96 48" stroke="#bcb5b0" stroke-width="1" fill="none"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#8f8a82" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#8f8a82" stroke-width="1.4" fill="none"/>
      <path d="M76 57 Q80 60 84 57" stroke="#8a4a44" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "miwa",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="miwaのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 44 Q52 62 56 150 L67 152 L65 66 Z" fill="#6b4a30"/>
      <path d="M98 44 Q108 62 104 150 L93 152 L95 66 Z" fill="#6b4a30"/>
      <polygon points="58,72 63,74 59,140" fill="#7d5738"/>
      <polygon points="102,72 97,74 101,140" fill="#7d5738"/>
      <path d="M73 138 L71 168 M87 138 L89 168" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="164" width="18" height="17" rx="5" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
      <rect x="80" y="164" width="18" height="17" rx="5" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
      <polygon points="65,74 95,74 100,138 60,138" fill="#f4a9b8"/>
      <polygon points="65,74 78,74 72,124" fill="#f8c3cd"/>
      <path d="M65 90 Q80 96 95 90 M64 108 Q80 114 96 108" stroke="#e88b9d" stroke-width="1.5" fill="none"/>
      <path d="M68 78 L58 84" stroke="#f4a9b8" stroke-width="7" stroke-linecap="round"/>
      <path d="M94 106 L58 84" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="49" y="78" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="114" rx="16" ry="13" fill="#c08a4a"/>
      <ellipse cx="94" cy="114" rx="6.5" ry="5.5" fill="#7a4e26"/>
      <path d="M92 108 L58 86" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M65 80 L60 86" stroke="#f4a9b8" stroke-width="7" stroke-linecap="round"/>
      <circle cx="59" cy="88" r="4.5" fill="#f2c9a4"/>
      <path d="M95 80 L97 100" stroke="#f4a9b8" stroke-width="7" stroke-linecap="round"/>
      <circle cx="97" cy="104" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 29 80 28 Q101 29 98 52 Q94 39 80 40 Q66 39 62 52 Z" fill="#6b4a30"/>
      <path d="M64 41 Q80 36 96 41" stroke="#8a6444" stroke-width="2.5" fill="none"/>
      <polygon points="67,34 78,31 72,41" fill="#87603e"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <path d="M76 58 Q80 61 84 58" stroke="#c07a70" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "三浦大知",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="三浦大知のダンス姿のイラスト">
      <ellipse cx="82" cy="188" rx="44" ry="6" fill="#dcdce3"/>
      <g stroke="#b8c4d6" stroke-width="2" stroke-linecap="round" fill="none">
        <path d="M30 96 L20 92 M32 108 L21 108 M34 120 L23 124"/>
        <path d="M126 70 L136 64 M128 82 L139 80"/>
      </g>
      <path d="M76 128 L58 156" stroke="#2c2c30" stroke-width="11" stroke-linecap="round"/>
      <path d="M84 128 L110 118" stroke="#2c2c30" stroke-width="11" stroke-linecap="round"/>
      <path d="M50 158 L62 170" stroke="#f2ede2" stroke-width="6" stroke-linecap="round"/>
      <rect x="46" y="166" width="17" height="9" rx="4" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1" transform="rotate(-18 54 170)"/>
      <path d="M112 116 L120 100" stroke="#f2ede2" stroke-width="6" stroke-linecap="round"/>
      <rect x="112" y="96" width="17" height="9" rx="4" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1" transform="rotate(-30 120 100)"/>
      <polygon points="70,78 92,74 96,130 66,132" fill="#2e2c30"/>
      <path d="M74 86 L86 84 M73 98 L85 96 M72 110 L84 108" stroke="#454249" stroke-width="1.4"/>
      <path d="M70 82 L52 106" stroke="#2e2c30" stroke-width="9" stroke-linecap="round"/>
      <path d="M52 106 Q46 110 48 116 M52 106 L46 104 M52 106 L47 112" stroke="#f2c9a4" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="51" cy="108" r="5" fill="#f2c9a4"/>
      <path d="M92 80 L108 60" stroke="#2e2c30" stroke-width="9" stroke-linecap="round"/>
      <circle cx="110" cy="57" r="5" fill="#f2c9a4"/>
      <rect x="107" y="40" width="6" height="18" rx="3" fill="#3a3a40" transform="rotate(22 110 49)"/>
      <circle cx="112" cy="38" r="5.5" fill="#9aa0ad"/>
      <rect x="77" y="63" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="81" cy="51" r="15" fill="#f2c9a4"/>
      <path d="M67 50 Q65 37 81 36 Q97 37 95 50 Q91 41 81 42 Q71 41 67 50 Z" fill="#241f20"/>
      <polygon points="72,39 81,37 76,45" fill="#3a3238"/>
      <circle cx="75" cy="51" r="1.6" fill="#3b3630"/>
      <circle cx="88" cy="51" r="1.6" fill="#3b3630"/>
      <path d="M71 47 Q75 45 78 47" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M85 47 Q88 45 92 47" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="81" cy="59" rx="2.6" ry="3" fill="#8a4a44"/>
    </svg>`,
  },
  {
    name: "野田洋次郎（RADWIMPS）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="野田洋次郎（RADWIMPS）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 138 L70 176 M88 138 L90 176" stroke="#3a3540" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="62,74 98,74 96,140 64,140" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1.2"/>
      <polygon points="62,74 74,74 68,132" fill="#e6e1d3"/>
      <path d="M74 74 L86 74 L84 108 L76 108 Z" fill="#efe9db"/>
      <path d="M66 76 L92 112" stroke="#6b4b33" stroke-width="4"/>
      <path d="M92 106 L58 86" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="49" y="78" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="118" rx="16" ry="13" fill="#c08a4a"/>
      <ellipse cx="94" cy="118" rx="6.5" ry="5.5" fill="#7a4e26"/>
      <path d="M92 112 L60 90" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M65 80 L60 90" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <circle cx="59" cy="93" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L97 104" stroke="#f4f1e9" stroke-width="9" stroke-linecap="round"/>
      <circle cx="97" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 54 Q58 30 80 29 Q102 30 98 54 L96 54 Q94 44 82 46 Q78 50 74 48 Q68 46 64 54 Z" fill="#2b2830"/>
      <path d="M62 54 Q60 44 66 40 L69 50 Z M98 54 Q100 44 94 40 L92 50 Z" fill="#2b2830"/>
      <path d="M64 48 Q72 44 80 46" stroke="#2b2830" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="73" cy="52" r="1.6" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.6" fill="#3b3630"/>
      <path d="M70 48 Q73 46 76 48" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 48 Q87 46 91 48" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M77 59 Q80 61 83 59" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "YUI",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="YUIのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 44 Q53 62 57 148 L67 150 L65 66 Z" fill="#a3764a"/>
      <path d="M98 44 Q107 62 103 148 L93 150 L95 66 Z" fill="#a3764a"/>
      <polygon points="59,72 64,74 60,140" fill="#b5885a"/>
      <polygon points="101,72 96,74 100,140" fill="#b5885a"/>
      <path d="M73 138 L71 168 M87 138 L89 168" stroke="#7089b0" stroke-width="9"/>
      <rect x="62" y="164" width="18" height="17" rx="5" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
      <rect x="80" y="164" width="18" height="17" rx="5" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
      <polygon points="65,74 95,74 99,138 61,138" fill="#a7d0e2"/>
      <polygon points="65,74 78,74 72,124" fill="#c2e0ec"/>
      <path d="M68 78 L58 84" stroke="#a7d0e2" stroke-width="7" stroke-linecap="round"/>
      <path d="M94 106 L58 84" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="49" y="78" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="114" rx="16" ry="13" fill="#c08a4a"/>
      <ellipse cx="94" cy="114" rx="6.5" ry="5.5" fill="#7a4e26"/>
      <path d="M92 108 L58 86" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M65 80 L60 86" stroke="#a7d0e2" stroke-width="7" stroke-linecap="round"/>
      <circle cx="59" cy="88" r="4.5" fill="#f2c9a4"/>
      <path d="M95 80 L97 100" stroke="#a7d0e2" stroke-width="7" stroke-linecap="round"/>
      <circle cx="97" cy="104" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 29 80 28 Q101 29 98 52 Q94 39 80 40 Q66 39 62 52 Z" fill="#a3764a"/>
      <path d="M63 44 Q80 39 97 44" stroke="#b88a5a" stroke-width="2.5" fill="none"/>
      <polygon points="67,34 78,31 72,41" fill="#bd9060"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <path d="M76 58 Q80 61 84 58" stroke="#c07a70" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "徳永英明",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="徳永英明のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#2c2c30" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#26242a"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#26242a"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#2e2c33"/>
      <polygon points="60,74 74,74 70,136 66,136" fill="#3a3840"/>
      <polygon points="86,74 100,74 97,136 92,136" fill="#26242a"/>
      <polygon points="74,74 86,74 84,110 76,110" fill="#454049"/>
      <path d="M66 78 L60 108" stroke="#2e2c33" stroke-width="9" stroke-linecap="round"/>
      <circle cx="59" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M94 78 L100 108" stroke="#2e2c33" stroke-width="9" stroke-linecap="round"/>
      <circle cx="101" cy="112" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 50 Q60 31 80 30 Q100 31 97 50 Q92 40 80 41 Q68 40 63 50 Z" fill="#6b6560"/>
      <path d="M64 44 Q80 39 96 44" stroke="#8a847e" stroke-width="2" fill="none"/>
      <path d="M65 48 Q72 45 78 47 M82 47 Q88 45 95 48" stroke="#7a746e" stroke-width="1.2" fill="none"/>
      <path d="M69 51 Q73 49 76 51" stroke="#3b3630" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="M84 51 Q87 49 91 51" stroke="#3b3630" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="59" rx="3" ry="3.8" fill="#8a3a44"/>
    </svg>`,
  },
  {
    name: "石原慎也（Saucy Dog）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="石原慎也（Saucy Dog）の3人のイラスト">
      <ellipse cx="80" cy="186" rx="62" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M23 132 L21 164 M31 132 L33 164" stroke="#3a3a44" stroke-width="6"/>
        <rect x="15" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="26" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="17,90 35,90 34,134 18,134" fill="#5a5f70"/>
        <path d="M28 104 L10 88" stroke="#4a3320" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="20" cy="112" rx="11" ry="9" fill="#b5793f"/>
        <ellipse cx="20" cy="112" rx="4.5" ry="3.5" fill="#7a4e26"/>
        <path d="M34 90 L40 96" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="41" cy="98" r="4" fill="#d9a878"/>
        <path d="M18 90 L14 96" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="13" cy="98" r="4" fill="#d9a878"/>
        <rect x="23.5" y="76" width="5" height="7" fill="#d9a878"/>
        <circle cx="26" cy="68" r="9" fill="#d9a878"/>
        <path d="M17 68 Q16 56 26 55 Q36 56 35 68 Q31 60 26 61 Q21 60 17 68 Z" fill="#6b4b33"/>
        <circle cx="22.5" cy="68" r="1.3" fill="#3b3630"/>
        <circle cx="29.5" cy="68" r="1.3" fill="#3b3630"/>
        <path d="M23.5 73 Q26 74.5 28.5 73" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M127 132 L125 164 M135 132 L137 164" stroke="#3a3a44" stroke-width="6"/>
        <rect x="119" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="130" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <path d="M124 66 Q119 78 121 110 L126 112 L125 76 Z" fill="#5a4a3a"/>
        <path d="M140 66 Q145 78 143 110 L138 112 L139 76 Z" fill="#5a4a3a"/>
        <polygon points="125,90 143,90 142,134 126,134" fill="#5a5f70"/>
        <rect x="120" y="104" width="26" height="9" rx="2" fill="#2c2c30"/>
        <path d="M124 104 L124 111 M129 104 L129 111 M134 104 L134 111 M139 104 L139 111" stroke="#c8ccd6" stroke-width="2.2"/>
        <path d="M126 92 L120 100" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <path d="M142 92 L148 100" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <rect x="131.5" y="76" width="5" height="7" fill="#d9a878"/>
        <circle cx="134" cy="68" r="9" fill="#d9a878"/>
        <path d="M125 68 Q124 56 134 55 Q144 56 143 68 Q139 60 134 61 Q129 60 125 68 Z" fill="#4a4038"/>
        <circle cx="130.5" cy="68" r="1.3" fill="#3b3630"/>
        <circle cx="137.5" cy="68" r="1.3" fill="#3b3630"/>
        <path d="M131.5 73 Q134 74.5 136.5 73" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M74 132 L72 172 M86 132 L88 172" stroke="#3a3540" stroke-width="9"/>
        <rect x="64" y="170" width="17" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
        <rect x="81" y="170" width="17" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
        <polygon points="64,72 96,72 94,132 66,132" fill="#e7ac5a"/>
        <polygon points="64,72 74,72 70,124" fill="#f0c078"/>
        <path d="M66 74 L92 108" stroke="#6b4b33" stroke-width="4"/>
        <path d="M92 102 L60 82" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
        <rect x="51" y="74" width="9" height="9" rx="2" fill="#4a3320"/>
        <ellipse cx="94" cy="114" rx="15" ry="12" fill="#c08a4a"/>
        <ellipse cx="94" cy="114" rx="6" ry="5" fill="#7a4e26"/>
        <path d="M92 108 L60 84" stroke="#e8d9c0" stroke-width="0.8"/>
        <path d="M65 76 L60 84" stroke="#e7ac5a" stroke-width="9" stroke-linecap="round"/>
        <circle cx="59" cy="87" r="4.5" fill="#f2c9a4"/>
        <path d="M95 76 L97 100" stroke="#e7ac5a" stroke-width="9" stroke-linecap="round"/>
        <circle cx="97" cy="103" r="4.5" fill="#f2c9a4"/>
        <rect x="76" y="60" width="8" height="8" fill="#f2c9a4"/>
        <circle cx="80" cy="48" r="15" fill="#f2c9a4"/>
        <path d="M64 48 Q61 27 80 26 Q99 27 96 48 Q92 36 80 37 Q68 36 64 48 Z" fill="#6b4b33"/>
        <path d="M64 48 Q62 40 68 37 L70 46 Z M96 48 Q98 40 92 37 L90 46 Z" fill="#6b4b33"/>
        <polygon points="68,32 78,30 72,40" fill="#87603e"/>
        <circle cx="74" cy="49" r="1.6" fill="#3b3630"/>
        <circle cx="86" cy="49" r="1.6" fill="#3b3630"/>
        <path d="M70 44 Q74 42 77 44" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <path d="M83 44 Q86 42 90 44" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <path d="M76 56 Q80 59 84 56" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      </g>
    </svg>`,
  },
  {
    name: "倉木麻衣",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="倉木麻衣のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 44 Q52 62 56 152 L67 154 L65 66 Z" fill="#6b4a30"/>
      <path d="M98 44 Q108 62 104 152 L93 154 L95 66 Z" fill="#6b4a30"/>
      <polygon points="58,72 63,74 59,144" fill="#7d5738"/>
      <polygon points="102,72 97,74 101,144" fill="#7d5738"/>
      <path d="M73 140 L71 168 M87 140 L89 168" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="164" width="18" height="17" rx="5" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
      <rect x="80" y="164" width="18" height="17" rx="5" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
      <polygon points="64,74 96,74 100,140 60,140" fill="#b7abd8"/>
      <polygon points="64,74 77,74 71,124" fill="#cbc1e6"/>
      <path d="M64 90 Q80 96 96 90 M63 108 Q80 114 97 108 M63 124 Q80 130 97 124" stroke="#9c8fc4" stroke-width="1.5" fill="none"/>
      <path d="M74 76 Q80 82 86 76 L88 84 L72 84 Z" fill="#c8bce4"/>
      <path d="M80 84 L77 100 L80 98 L83 100 Z" fill="#d4a947"/>
      <circle cx="80" cy="82" r="2" fill="#d4a947"/>
      <path d="M64 80 L54 104" stroke="#b7abd8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="52" cy="108" r="5" fill="#f2c9a4"/>
      <path d="M96 80 L106 104" stroke="#b7abd8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="108" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 29 80 28 Q101 29 98 52 Q94 39 80 40 Q66 39 62 52 Z" fill="#6b4a30"/>
      <path d="M64 42 Q80 37 96 42" stroke="#8a6444" stroke-width="2.5" fill="none"/>
      <polygon points="67,34 78,31 72,41" fill="#87603e"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <ellipse cx="92" cy="56" rx="2.6" ry="1.6" fill="#f2b2ac"/>
      <path d="M76 58 Q80 61 84 58" stroke="#c07a70" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "Fukase（SEKAI NO OWARI）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Fukase（SEKAI NO OWARI）の4人のイラスト">
      <ellipse cx="80" cy="186" rx="62" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M23 132 L21 164 M31 132 L33 164" stroke="#3a3a44" stroke-width="6"/>
        <rect x="15" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="26" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="17,90 35,90 34,134 18,134" fill="#4a5a6b"/>
        <path d="M28 104 L10 88" stroke="#4a3320" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="20" cy="112" rx="11" ry="9" fill="#b5793f"/>
        <ellipse cx="20" cy="112" rx="4.5" ry="3.5" fill="#7a4e26"/>
        <path d="M34 90 L40 96" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="41" cy="98" r="4" fill="#d9a878"/>
        <rect x="23.5" y="76" width="5" height="7" fill="#d9a878"/>
        <circle cx="26" cy="68" r="9" fill="#d9a878"/>
        <path d="M17 68 Q16 56 26 55 Q36 56 35 68 Q31 60 26 61 Q21 60 17 68 Z" fill="#2e2a30"/>
        <circle cx="22.5" cy="68" r="1.3" fill="#3b3630"/>
        <circle cx="29.5" cy="68" r="1.3" fill="#3b3630"/>
        <path d="M23.5 73 Q26 74.5 28.5 73" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M59 132 L57 164 M67 132 L69 164" stroke="#3a3540" stroke-width="6"/>
        <rect x="51" y="162" width="13" height="7" rx="3.5" fill="#26242a"/>
        <rect x="62" y="162" width="13" height="7" rx="3.5" fill="#26242a"/>
        <polygon points="53,90 71,90 70,134 54,134" fill="#33313a"/>
        <path d="M54 92 L48 100" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <path d="M70 92 Q76 98 73 104" stroke="#d9a878" stroke-width="5" fill="none" stroke-linecap="round"/>
        <circle cx="47" cy="102" r="4" fill="#d9a878"/>
        <rect x="66" y="80" width="5.5" height="14" rx="2.5" fill="#3a3a40" transform="rotate(-18 69 86)"/>
        <circle cx="71" cy="78" r="4.5" fill="#9aa0ad"/>
        <rect x="59.5" y="76" width="5" height="7" fill="#d9a878"/>
        <circle cx="62" cy="68" r="9" fill="#d9a878"/>
        <path d="M53 68 Q52 55 62 54 Q72 55 71 68 Q67 59 62 60 Q57 59 53 68 Z" fill="#2b2724"/>
        <polygon points="57,57 64,55 59,63" fill="#403a36"/>
        <circle cx="58.5" cy="68" r="1.3" fill="#3b3630"/>
        <circle cx="65.5" cy="68" r="1.3" fill="#3b3630"/>
        <path d="M59.5 73 Q62 74.5 64.5 73" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M95 132 L93 168 M105 132 L107 168" stroke="#c9bfa8" stroke-width="7"/>
        <rect x="86" y="166" width="15" height="8" rx="4" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="100" y="166" width="15" height="8" rx="4" fill="#e7dfce" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="88,84 112,84 116,132 84,132" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
        <polygon points="88,84 97,84 92,128 88,128" fill="#e2dccb"/>
        <path d="M100 84 L100 130" stroke="#d4cdba" stroke-width="1.4"/>
        <path d="M90 86 L82 100" stroke="#f0ece1" stroke-width="7" stroke-linecap="round"/>
        <circle cx="80" cy="103" r="4" fill="#f2c9a4"/>
        <path d="M110 86 L118 100" stroke="#f0ece1" stroke-width="7" stroke-linecap="round"/>
        <circle cx="120" cy="103" r="4" fill="#f2c9a4"/>
        <rect x="96" y="72" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="100" cy="64" r="10" fill="#f2c9a4"/>
        <path d="M89 64 Q86 46 100 45 Q114 46 111 64 L108 64 Q109 52 100 53 Q91 52 92 64 Z" fill="#3a2e26"/>
        <path d="M89 64 Q88 74 92 80 L95 66 Z" fill="#3a2e26"/>
        <path d="M111 64 Q112 74 108 80 L105 66 Z" fill="#3a2e26"/>
        <circle cx="96.5" cy="64" r="1.4" fill="#3b3630"/>
        <circle cx="103.5" cy="64" r="1.4" fill="#3b3630"/>
        <ellipse cx="100" cy="70" rx="2" ry="2.4" fill="#8a4a44"/>
      </g>
      <g>
        <path d="M131 132 L129 164 M139 132 L141 164" stroke="#5a5f70" stroke-width="6"/>
        <rect x="123" y="162" width="13" height="7" rx="3.5" fill="#3a3a40"/>
        <rect x="134" y="162" width="13" height="7" rx="3.5" fill="#3a3a40"/>
        <polygon points="125,90 143,90 142,134 126,134" fill="#6b7080"/>
        <path d="M126 92 L120 100 M142 92 L148 100" stroke="#f2c9a4" stroke-width="5" stroke-linecap="round"/>
        <circle cx="119" cy="102" r="4" fill="#f2c9a4"/>
        <circle cx="149" cy="102" r="4" fill="#f2c9a4"/>
        <rect x="131.5" y="78" width="5" height="6" fill="#f2c9a4"/>
        <circle cx="134" cy="71" r="9.5" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1.2"/>
        <path d="M134 61.5 Q127 63 126 71 L142 71 Q141 63 134 61.5 Z" fill="#eae5da"/>
        <circle cx="130" cy="71" r="1.6" fill="#3b3630"/>
        <circle cx="138" cy="71" r="1.6" fill="#3b3630"/>
        <path d="M129 66 Q131 64 133 66 M135 66 Q137 64 139 66" stroke="#bcb5a4" stroke-width="1.1" fill="none"/>
        <ellipse cx="134" cy="76" rx="2.2" ry="1.4" fill="#d88a8a"/>
        <path d="M131 74.5 Q134 77 137 74.5" stroke="#c05a5a" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
    </svg>`,
  },
];
