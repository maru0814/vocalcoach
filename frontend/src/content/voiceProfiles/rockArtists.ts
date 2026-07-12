import type { ProfileArtist } from "./types";

// Rockタイプの有名人イラスト（docs/62 §6-1 確定版v3）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。

export const ROCK_ARTISTS: ProfileArtist[] = [
  {
    name: "LiSA",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="LiSAのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M60 34 L44 42 L52 54 L40 66 L50 78 L42 94 L54 98 L60 66 Z" fill="#d84a63"/>
      <path d="M100 34 L116 42 L108 54 L120 66 L110 78 L118 94 L106 98 L100 66 Z" fill="#d84a63"/>
      <polygon points="50,48 56,44 52,62" fill="#ed93b1"/>
      <polygon points="110,48 104,44 108,62" fill="#ed93b1"/>
      <path d="M72 132 L70 170 M88 132 L90 170" stroke="#3a3540" stroke-width="10"/>
      <path d="M68 138 L76 146 M67 150 L75 158 M84 138 L92 146 M85 150 L93 158" stroke="#5c5668" stroke-width="1.2"/>
      <rect x="61" y="166" width="19" height="17" rx="4" fill="#211e22"/>
      <rect x="81" y="166" width="19" height="17" rx="4" fill="#211e22"/>
      <path d="M63 172 L78 172 M83 172 L98 172" stroke="#4a4650" stroke-width="1.5"/>
      <polygon points="63,74 97,74 96,104 64,104" fill="#2c2a30"/>
      <polygon points="64,104 96,104 103,132 57,132" fill="#c9303c"/>
      <path d="M70 106 L67 130 M80 104 L80 132 M90 106 L93 130" stroke="#8f1f28" stroke-width="2.5"/>
      <path d="M60 118 L100 118" stroke="#8f1f28" stroke-width="2.5"/>
      <path d="M62 111 L99 111 M61 125 L101 125" stroke="#f2d7d7" stroke-width="0.8"/>
      <path d="M66 84 L54 108" stroke="#2c2a30" stroke-width="9" stroke-linecap="round"/>
      <circle cx="53" cy="112" r="5" fill="#f2c9a4"/>
      <rect x="47" y="103" width="10" height="4" rx="2" fill="#c9303c"/>
      <path d="M95 80 L110 52" stroke="#2c2a30" stroke-width="9" stroke-linecap="round"/>
      <circle cx="112" cy="49" r="5.5" fill="#f2c9a4"/>
      <rect x="109" y="30" width="6" height="16" rx="3" fill="#3a3a40" transform="rotate(14 112 38)"/>
      <circle cx="110" cy="28" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 48 Q62 30 80 30 Q98 30 97 48 Q90 40 80 41 Q70 40 63 48 Z" fill="#c9354f"/>
      <polygon points="70,33 77,31 73,40" fill="#e8b84a"/>
      <circle cx="60" cy="38" r="3" fill="#2c2a30"/>
      <circle cx="100" cy="38" r="3" fill="#2c2a30"/>
      <path d="M70 51 Q73 53 76 51" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="59" rx="3.2" ry="4" fill="#8a3a44"/>
    </svg>`,
  },
  {
    name: "Mr.Children",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Mr.Childrenのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 132 L70 176 M88 132 L90 176" stroke="#5a7396" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="62,74 98,74 95,134 65,134" fill="#3b4a6b"/>
      <polygon points="74,74 86,74 84,112 76,112" fill="#f2f0ea"/>
      <path d="M66 76 L92 110" stroke="#6b4b33" stroke-width="4"/>
      <path d="M92 106 L58 84" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="49" y="76" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="94" cy="116" rx="16" ry="13" fill="#c08a4a"/>
      <ellipse cx="94" cy="116" rx="6.5" ry="5.5" fill="#7a4e26"/>
      <path d="M92 110 L60 88" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M65 80 L60 88" stroke="#3b4a6b" stroke-width="9" stroke-linecap="round"/>
      <circle cx="60" cy="90" r="5" fill="#f2c9a4"/>
      <path d="M95 80 L97 104" stroke="#3b4a6b" stroke-width="9" stroke-linecap="round"/>
      <circle cx="96" cy="108" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 50 Q61 32 80 31 Q99 32 97 50 Q94 38 80 39 Q66 38 63 50 Z" fill="#5c4030"/>
      <polygon points="68,35 76,33 71,41" fill="#755440"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M75 58 Q80 62 85 58" stroke="#8a4a44" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "浜崎あゆみ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="浜崎あゆみのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 40 Q48 60 52 138 L66 142 L64 62 Z" fill="#eddca6"/>
      <path d="M98 40 Q112 60 108 138 L94 142 L96 62 Z" fill="#eddca6"/>
      <polygon points="56,70 62,72 58,120" fill="#f8ecc9"/>
      <polygon points="104,70 98,72 102,120" fill="#f8ecc9"/>
      <path d="M73 124 L71 160 M87 124 L89 160" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="62" y="156" width="18" height="27" rx="6" fill="#f5f0e4" stroke="#c2baa8" stroke-width="1.2"/>
      <rect x="80" y="156" width="18" height="27" rx="6" fill="#f5f0e4" stroke="#c2baa8" stroke-width="1.2"/>
      <path d="M62 178 L80 178 M80 178 L98 178" stroke="#b9b2a2" stroke-width="1.5"/>
      <polygon points="66,74 94,74 100,124 60,124" fill="#f4c0d1"/>
      <polygon points="66,74 79,74 72,112" fill="#fad4e0"/>
      <path d="M60 124 L100 124" stroke="#d4a947" stroke-width="2.5"/>
      <polygon points="88,98 89.5,102 94,102 90.5,105 92,109 88,106 84,109 85.5,105 82,102 86.5,102" fill="#fff"/>
      <polygon points="70,110 71.2,113 74,113 71.8,115 73,118 70,116 67,118 68.2,115 66,113 68.8,113" fill="#fff"/>
      <path d="M74 78 Q80 84 86 78" stroke="#d4a947" stroke-width="1" fill="none"/>
      <path d="M80 84 L76.5 93 L79 93 L80 89 L81 93 L83.5 93 Z" fill="#d4a947"/>
      <path d="M66 82 L58 108" stroke="#f2c9a4" stroke-width="8" stroke-linecap="round"/>
      <path d="M58 108 Q64 112 66 106" stroke="#f2c9a4" stroke-width="8" stroke-linecap="round" fill="none"/>
      <path d="M94 80 L108 56" stroke="#f2c9a4" stroke-width="8" stroke-linecap="round"/>
      <circle cx="110" cy="52" r="5.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 50 Q60 29 80 28 Q100 29 97 50 Q92 34 72 40 Q65 43 63 50 Z" fill="#e8ca86"/>
      <polygon points="68,34 78,30 71,41" fill="#f4dfa8"/>
      <polygon points="122,32 124,38 130,38 125,42 127,48 122,44 117,48 119,42 114,38 120,38" fill="#d4a947"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M70 48 L68 46 M76 48 L78 46 M84 48 L82 46 M90 48 L92 46" stroke="#3b3630" stroke-width="1"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M76 58 Q80 61 84 58" stroke="#c05a70" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "B'z",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="B'z（松本孝弘と稲葉浩志）のイラスト">
      <ellipse cx="80" cy="188" rx="52" ry="6" fill="#dcdce3"/>
      <path d="M42 134 L40 172 M52 134 L54 172" stroke="#26242a" stroke-width="8"/>
      <rect x="33" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <rect x="47" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <polygon points="34,76 60,76 58,136 36,136" fill="#33313a"/>
      <path d="M48 102 L22 84" stroke="#4a3320" stroke-width="4.5" stroke-linecap="round"/>
      <rect x="14" y="76" width="9" height="9" rx="2" fill="#2c2420"/>
      <ellipse cx="50" cy="110" rx="14" ry="11" fill="#c0392b"/>
      <polygon points="42,104 52,102 46,116" fill="#e05545"/>
      <ellipse cx="54" cy="112" rx="5" ry="4" fill="#f2ede2"/>
      <path d="M48 106 L24 88" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M58 84 L57 100" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="56" cy="103" r="4.5" fill="#f2c9a4"/>
      <path d="M36 84 L30 88" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="29" cy="89" r="4.5" fill="#f2c9a4"/>
      <rect x="43" y="65" width="7" height="8" fill="#f2c9a4"/>
      <circle cx="46" cy="56" r="13" fill="#f2c9a4"/>
      <path d="M33 54 Q32 40 46 39 Q60 40 59 54 Q55 44 46 45 Q37 44 33 54 Z" fill="#33302c"/>
      <rect x="36" y="52" width="20" height="6" rx="3" fill="#1d1b1e"/>
      <path d="M36 54 L33 52 M56 54 L59 52" stroke="#1d1b1e" stroke-width="1.6"/>
      <path d="M42 63 Q46 65 50 63" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M106 134 L104 172 M118 134 L120 172" stroke="#1f1f24" stroke-width="8"/>
      <rect x="97" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <rect x="111" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <polygon points="100,78 124,78 122,136 102,136" fill="#2c2c31"/>
      <path d="M100 80 Q97 74 104 72 M124 80 Q127 74 120 72" stroke="#f2c9a4" stroke-width="5" stroke-linecap="round" fill="none"/>
      <path d="M123 82 L134 50" stroke="#f2c9a4" stroke-width="9" stroke-linecap="round"/>
      <circle cx="135" cy="45" r="6" fill="#f2c9a4"/>
      <path d="M101 84 L103 68" stroke="#f2c9a4" stroke-width="8" stroke-linecap="round"/>
      <circle cx="104" cy="65" r="4.5" fill="#f2c9a4"/>
      <rect x="103" y="52" width="5.5" height="13" rx="2.5" fill="#3a3a40" transform="rotate(-18 106 58)"/>
      <circle cx="109" cy="50" r="5" fill="#9aa0ad"/>
      <circle cx="112" cy="80" r="1.6" fill="#c8ccd6"/>
      <rect x="108" y="66" width="7" height="8" fill="#f2c9a4"/>
      <circle cx="112" cy="57" r="13" fill="#f2c9a4"/>
      <path d="M98 58 Q96 41 112 40 Q128 41 126 58 Q123 46 112 47 Q101 46 98 58 Z" fill="#2e2a28"/>
      <path d="M97 52 Q95 60 99 64 L101 56 Z" fill="#2e2a28"/>
      <circle cx="107" cy="57" r="1.5" fill="#3b3630"/>
      <circle cx="117" cy="57" r="1.5" fill="#3b3630"/>
      <path d="M103 52 Q107 50 110 52 M114 52 Q117 50 121 52" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="112" cy="65" rx="3" ry="3.6" fill="#7d3b3b"/>
    </svg>`,
  },
  {
    name: "YUKI",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="YUKIのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M74 134 L72 170 M86 134 L88 170" stroke="#e6e0d2" stroke-width="8"/>
      <rect x="63" y="168" width="18" height="10" rx="5" fill="#c9303c"/>
      <rect x="80" y="168" width="18" height="10" rx="5" fill="#c9303c"/>
      <polygon points="66,74 94,74 101,134 59,134" fill="#e24b4a"/>
      <circle cx="73" cy="86" r="2.2" fill="#fff"/>
      <circle cx="87" cy="92" r="2.2" fill="#fff"/>
      <circle cx="78" cy="104" r="2.2" fill="#fff"/>
      <circle cx="69" cy="118" r="2.2" fill="#fff"/>
      <circle cx="89" cy="120" r="2.2" fill="#fff"/>
      <circle cx="80" cy="128" r="2.2" fill="#fff"/>
      <path d="M74 74 Q77 80 80 74 Q83 80 86 74 L86 76 Q83 82 80 76 Q77 82 74 76 Z" fill="#fff"/>
      <circle cx="65" cy="80" r="6" fill="#e24b4a"/>
      <circle cx="95" cy="80" r="6" fill="#e24b4a"/>
      <path d="M95 78 L103 62" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
      <circle cx="104" cy="59" r="4.5" fill="#f2c9a4"/>
      <path d="M65 82 L54 98" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
      <circle cx="52" cy="101" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 56 Q58 30 80 29 Q102 30 98 56 L94 58 Q97 46 93 42 L67 42 Q63 46 66 58 Z" fill="#33302e"/>
      <polygon points="62,56 66,58 60,64" fill="#33302e"/>
      <polygon points="98,56 94,58 100,64" fill="#33302e"/>
      <polygon points="68,34 78,32 72,40" fill="#4a4643"/>
      <polygon points="67,37 70,41 64,41" fill="#e8b84a"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <ellipse cx="68" cy="56" rx="2.8" ry="1.7" fill="#f0999b"/>
      <ellipse cx="92" cy="56" rx="2.8" ry="1.7" fill="#f0999b"/>
      <ellipse cx="80" cy="59" rx="2.8" ry="3.4" fill="#8a4a44"/>
    </svg>`,
  },
  {
    name: "優里",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="優里のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#2c2c30" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efece3" stroke="#bfb9ac" stroke-width="1"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#2e2c30"/>
      <path d="M68 74 Q72 80 80 80 Q88 80 92 74" stroke="#454249" stroke-width="3" fill="none"/>
      <path d="M76 82 L76 92 M84 82 L84 92" stroke="#54515a" stroke-width="1.6"/>
      <circle cx="76" cy="93" r="1.4" fill="#54515a"/>
      <circle cx="84" cy="93" r="1.4" fill="#54515a"/>
      <path d="M66 78 L94 112" stroke="#4a4650" stroke-width="4"/>
      <path d="M94 104 L122 76" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="70" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="92" cy="114" rx="17" ry="14" fill="#c08a4a"/>
      <ellipse cx="92" cy="114" rx="7" ry="6" fill="#7a4e26"/>
      <path d="M94 108 L120 80" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M63 82 L58 108" stroke="#2e2c30" stroke-width="9" stroke-linecap="round"/>
      <circle cx="58" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M97 82 L98 100" stroke="#2e2c30" stroke-width="9" stroke-linecap="round"/>
      <circle cx="98" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q60 27 80 26 Q100 27 98 50 L94 50 Q95 37 80 37 Q65 37 66 50 Z" fill="#3d3d43"/>
      <path d="M64 43 Q80 39 96 43" stroke="#55555c" stroke-width="2.5" fill="none"/>
      <path d="M75 55.5 Q80 57.5 85 55.5" stroke="#4a3b2e" stroke-width="2" fill="none" stroke-linecap="round"/>
      <path d="M75 63 Q80 66 85 63 L84 60 Q80 62 76 60 Z" fill="#4a3b2e"/>
      <circle cx="73" cy="50" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="50" r="1.7" fill="#3b3630"/>
      <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M77 59 Q80 60.5 83 59" stroke="#6d4438" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "SPEED",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="SPEEDの4人のイラスト">
      <ellipse cx="80" cy="186" rx="62" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M23 132 L21 164 M29 132 L31 164" stroke="#8a8d6a" stroke-width="6"/>
        <rect x="15" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="26" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="17,89 35,89 34,104 18,104" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="19" y="104" width="14" height="5" fill="#d9a878"/>
        <polygon points="17,109 35,109 34,134 18,134" fill="#8a8d6a"/>
        <path d="M18 96 L10 84 M34 96 L42 84" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="9" cy="81" r="3.5" fill="#d9a878"/>
        <circle cx="43" cy="81" r="3.5" fill="#d9a878"/>
        <rect x="23.5" y="83" width="5" height="6" fill="#d9a878"/>
        <circle cx="26" cy="76" r="9" fill="#d9a878"/>
        <path d="M17 77 Q16 66 26 65 Q36 66 35 77 Q31 70 26 71 Q21 70 17 77 Z" fill="#3a2e26"/>
        <circle cx="18" cy="66" r="4" fill="#3a2e26"/>
        <circle cx="34" cy="66" r="4" fill="#3a2e26"/>
        <circle cx="22.5" cy="77" r="1.3" fill="#3b3630"/>
        <circle cx="29.5" cy="77" r="1.3" fill="#3b3630"/>
        <path d="M23.5 82 Q26 83.5 28.5 82" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M59 132 L57 164 M65 132 L67 164" stroke="#8a8d6a" stroke-width="6"/>
        <rect x="51" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="62" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="53,89 71,89 70,104 54,104" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="55" y="104" width="14" height="5" fill="#d9a878"/>
        <polygon points="53,109 71,109 70,134 54,134" fill="#8a8d6a"/>
        <path d="M54 96 L46 106 M70 96 L78 84" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="45" cy="109" r="3.5" fill="#d9a878"/>
        <circle cx="79" cy="81" r="3.5" fill="#d9a878"/>
        <rect x="59.5" y="83" width="5" height="6" fill="#d9a878"/>
        <circle cx="62" cy="76" r="9" fill="#d9a878"/>
        <path d="M53 77 Q52 66 62 65 Q72 66 71 77 Q67 70 62 71 Q57 70 53 77 Z" fill="#3a2e26"/>
        <circle cx="70" cy="64" r="4.5" fill="#3a2e26"/>
        <path d="M73 66 Q78 72 75 80" stroke="#3a2e26" stroke-width="3" fill="none" stroke-linecap="round"/>
        <circle cx="58.5" cy="77" r="1.3" fill="#3b3630"/>
        <circle cx="65.5" cy="77" r="1.3" fill="#3b3630"/>
        <ellipse cx="62" cy="82.5" rx="1.8" ry="2.2" fill="#8a4a44"/>
      </g>
      <g>
        <path d="M95 132 L93 164 M101 132 L103 164" stroke="#8a8d6a" stroke-width="6"/>
        <rect x="87" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="98" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="89,89 107,89 106,104 90,104" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="91" y="104" width="14" height="5" fill="#d9a878"/>
        <polygon points="89,109 107,109 106,134 90,134" fill="#8a8d6a"/>
        <path d="M90 96 L82 84 M106 96 L114 106" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="81" cy="81" r="3.5" fill="#d9a878"/>
        <circle cx="115" cy="109" r="3.5" fill="#d9a878"/>
        <rect x="95.5" y="83" width="5" height="6" fill="#d9a878"/>
        <circle cx="98" cy="76" r="9" fill="#d9a878"/>
        <path d="M89 80 Q87 65 98 64 Q109 65 107 80 L104 80 Q106 70 98 70 Q90 70 92 80 Z" fill="#3a2e26"/>
        <circle cx="94.5" cy="77" r="1.3" fill="#3b3630"/>
        <circle cx="101.5" cy="77" r="1.3" fill="#3b3630"/>
        <path d="M95.5 82 Q98 83.5 100.5 82" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M131 132 L129 164 M137 132 L139 164" stroke="#8a8d6a" stroke-width="6"/>
        <rect x="123" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="134" y="162" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <path d="M127 68 Q122 80 124 112 L129 114 L128 78 Z" fill="#3a2e26"/>
        <path d="M141 68 Q146 80 144 112 L139 114 L140 78 Z" fill="#3a2e26"/>
        <polygon points="125,89 143,89 142,104 126,104" fill="#f7f5f0" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="127" y="104" width="14" height="5" fill="#d9a878"/>
        <polygon points="125,109 143,109 142,134 126,134" fill="#8a8d6a"/>
        <path d="M126 96 L118 84 M142 96 L150 88" stroke="#d9a878" stroke-width="5" stroke-linecap="round"/>
        <circle cx="117" cy="81" r="3.5" fill="#d9a878"/>
        <circle cx="151" cy="86" r="3.5" fill="#d9a878"/>
        <rect x="131.5" y="83" width="5" height="6" fill="#d9a878"/>
        <circle cx="134" cy="76" r="9" fill="#d9a878"/>
        <path d="M125 77 Q124 66 134 65 Q144 66 143 77 Q139 70 134 71 Q129 70 125 77 Z" fill="#3a2e26"/>
        <circle cx="130.5" cy="77" r="1.3" fill="#3b3630"/>
        <circle cx="137.5" cy="77" r="1.3" fill="#3b3630"/>
        <ellipse cx="134" cy="82.5" rx="1.8" ry="2.2" fill="#8a4a44"/>
      </g>
    </svg>`,
  },
  {
    name: "ポルノグラフィティ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="ポルノグラフィティ（新藤晴一と岡野昭仁）のイラスト">
      <ellipse cx="80" cy="188" rx="52" ry="6" fill="#dcdce3"/>
      <path d="M42 134 L40 172 M52 134 L54 172" stroke="#26242a" stroke-width="8"/>
      <rect x="33" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <rect x="47" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
      <path d="M36 50 Q35 60 38 66 L41 58 Z M56 50 Q57 60 54 66 L51 58 Z" fill="#33302c"/>
      <polygon points="34,76 60,76 58,136 36,136" fill="#3a3138"/>
      <path d="M48 102 L22 84" stroke="#4a3320" stroke-width="4.5" stroke-linecap="round"/>
      <rect x="14" y="76" width="9" height="9" rx="2" fill="#2c2420"/>
      <ellipse cx="50" cy="110" rx="14" ry="11" fill="#b5793f"/>
      <ellipse cx="50" cy="110" rx="9" ry="7" fill="#8a5a2e"/>
      <ellipse cx="50" cy="110" rx="4.5" ry="3.5" fill="#4a3320"/>
      <path d="M48 106 L24 88" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M58 84 L57 100" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="56" cy="103" r="4.5" fill="#f2c9a4"/>
      <path d="M36 84 L30 88" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
      <circle cx="29" cy="89" r="4.5" fill="#f2c9a4"/>
      <rect x="43" y="65" width="7" height="8" fill="#f2c9a4"/>
      <circle cx="46" cy="56" r="13" fill="#f2c9a4"/>
      <path d="M34 54 Q33 42 46 41 Q59 42 58 54 Q54 45 46 46 Q38 45 34 54 Z" fill="#33302c"/>
      <ellipse cx="46" cy="42" rx="16" ry="3.5" fill="#2b2724"/>
      <path d="M37 42 Q37 30 46 30 Q55 30 55 42 Z" fill="#2b2724"/>
      <path d="M37 39 L55 39" stroke="#6b5a3e" stroke-width="2"/>
      <circle cx="41.5" cy="56" r="1.5" fill="#3b3630"/>
      <circle cx="50.5" cy="56" r="1.5" fill="#3b3630"/>
      <path d="M38 52 Q41 50 44 52 M48 52 Q51 50 54 52" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <path d="M43 62 Q46 63.5 49 62" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M106 134 L104 172 M118 134 L120 172" stroke="#2c2c30" stroke-width="8"/>
      <rect x="97" y="170" width="16" height="8" rx="4" fill="#211e22"/>
      <rect x="111" y="170" width="16" height="8" rx="4" fill="#211e22"/>
      <polygon points="100,76 124,76 122,136 102,136" fill="#454049"/>
      <polygon points="100,76 109,76 104,106" fill="#565060"/>
      <path d="M108 78 Q112 84 116 78" stroke="#c8ccd6" stroke-width="1.3" fill="none"/>
      <path d="M122 80 L128 64" stroke="#454049" stroke-width="8" stroke-linecap="round"/>
      <circle cx="129" cy="61" r="5" fill="#f2c9a4"/>
      <rect x="124" y="48" width="5.5" height="13" rx="2.5" fill="#3a3a40" transform="rotate(20 127 54)"/>
      <circle cx="123" cy="46" r="5" fill="#9aa0ad"/>
      <path d="M102 82 L94 104" stroke="#454049" stroke-width="8" stroke-linecap="round"/>
      <circle cx="93" cy="108" r="4.5" fill="#f2c9a4"/>
      <rect x="108" y="65" width="7" height="8" fill="#f2c9a4"/>
      <circle cx="112" cy="56" r="13" fill="#f2c9a4"/>
      <path d="M99 56 Q98 41 112 40 Q126 41 125 56 Q121 44 112 45 Q103 44 99 56 Z" fill="#2b2724"/>
      <polygon points="104,43 112,41 107,49" fill="#403a36"/>
      <circle cx="107" cy="56" r="1.5" fill="#3b3630"/>
      <circle cx="117" cy="56" r="1.5" fill="#3b3630"/>
      <path d="M103 51 Q107 49 110 51 M114 51 Q117 49 121 51" stroke="#3b3630" stroke-width="1.3" fill="none"/>
      <ellipse cx="112" cy="63" rx="3" ry="3.8" fill="#7d3b3b"/>
    </svg>`,
  },
  {
    name: "CHIKA（HANA）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="CHIKA（HANA）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M63 42 Q54 60 57 138 L69 140 L66 66 Z" fill="#241f26"/>
      <path d="M97 42 Q106 60 103 138 L91 140 L94 66 Z" fill="#241f26"/>
      <polygon points="60,116 66,116 63,140" fill="#e05a8a"/>
      <polygon points="100,116 94,116 97,140" fill="#e05a8a"/>
      <path d="M72 140 L70 172 M88 140 L90 172" stroke="#c9b48f" stroke-width="12"/>
      <rect x="60" y="170" width="20" height="11" rx="5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
      <rect x="80" y="170" width="20" height="11" rx="5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
      <path d="M60 178 L80 178 M80 178 L100 178" stroke="#b9b2a2" stroke-width="1.6"/>
      <polygon points="66,74 94,74 92,98 68,98" fill="#26232a"/>
      <rect x="69" y="98" width="22" height="7" fill="#e0b28a"/>
      <polygon points="64,105 96,105 100,140 60,140" fill="#c9b48f"/>
      <path d="M60 112 L100 112" stroke="#6b5a3e" stroke-width="2.5"/>
      <path d="M68 120 L72 120 L72 128 L68 128 Z M88 120 L92 120 L92 128 L88 128 Z" fill="none" stroke="#a8946e" stroke-width="1.4"/>
      <path d="M72 76 Q80 84 88 76" stroke="#c8ccd6" stroke-width="1.6" fill="none"/>
      <circle cx="80" cy="82" r="1.8" fill="#c8ccd6"/>
      <path d="M66 80 Q58 90 62 100" stroke="#e0b28a" stroke-width="7" fill="none" stroke-linecap="round"/>
      <path d="M94 80 L100 106" stroke="#e0b28a" stroke-width="7" stroke-linecap="round"/>
      <circle cx="101" cy="110" r="4.5" fill="#e0b28a"/>
      <rect x="98" y="112" width="6" height="15" rx="3" fill="#3a3a40"/>
      <circle cx="101" cy="130" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#e0b28a"/>
      <circle cx="80" cy="50" r="16" fill="#e0b28a"/>
      <circle cx="63" cy="60" r="4" fill="none" stroke="#d4a947" stroke-width="1.8"/>
      <circle cx="97" cy="60" r="4" fill="none" stroke="#d4a947" stroke-width="1.8"/>
      <path d="M62 54 Q60 28 80 27 Q100 28 98 54 Q96 36 86 37 Q83 42 80 42 Q77 42 74 37 Q64 36 62 54 Z" fill="#241f26"/>
      <polygon points="67,33 76,30 71,39" fill="#3a3040"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.5" fill="none"/>
      <path d="M76 58 Q81 61 85 57" stroke="#b0566a" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "Mrs.GREEN APPLE",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Mrs.GREEN APPLEの3人のイラスト">
      <ellipse cx="80" cy="188" rx="56" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M32 130 L30 168 M42 130 L44 168" stroke="#4a4a52" stroke-width="7"/>
        <rect x="23" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <rect x="37" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="26,80 48,80 46,132 28,132" fill="#5c5464"/>
        <path d="M38 100 L18 86" stroke="#4a3320" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="40" cy="108" rx="11" ry="9" fill="#b5793f"/>
        <ellipse cx="40" cy="108" rx="4.5" ry="3.5" fill="#7a4e26"/>
        <path d="M28 86 L24 92" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="23" cy="94" r="4" fill="#f2c9a4"/>
        <path d="M46 86 L46 98" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="45" cy="101" r="4" fill="#f2c9a4"/>
        <rect x="34" y="70" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="37" cy="62" r="11" fill="#f2c9a4"/>
        <path d="M26 62 Q25 50 37 49 Q49 50 48 62 Q47 55 43 57 Q45 52 40 54 Q41 50 36 53 Q37 50 32 54 Q28 55 26 62 Z" fill="#6b4b33"/>
        <circle cx="33" cy="62" r="1.4" fill="#3b3630"/>
        <circle cx="41" cy="62" r="1.4" fill="#3b3630"/>
        <path d="M34 67 Q37 69 40 67" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M118 130 L116 168 M128 130 L130 168" stroke="#4a4a52" stroke-width="7"/>
        <rect x="109" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <rect x="123" y="166" width="15" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="112,80 134,80 132,132 114,132" fill="#5c5464"/>
        <rect x="106" y="98" width="30" height="11" rx="2" fill="#2c2c30"/>
        <path d="M110 98 L110 106 M115 98 L115 106 M120 98 L120 106 M125 98 L125 106 M130 98 L130 106" stroke="#f2f0ea" stroke-width="2.6"/>
        <path d="M112 86 L108 96" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <path d="M134 86 L136 96" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <rect x="120" y="70" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="123" cy="62" r="11" fill="#f2c9a4"/>
        <path d="M112 62 Q111 50 123 49 Q135 50 134 62 Q131 53 123 54 Q115 53 112 62 Z" fill="#8a6a4a"/>
        <polygon points="116,53 123,51 118,58" fill="#a3805c"/>
        <circle cx="119" cy="62" r="1.4" fill="#3b3630"/>
        <circle cx="127" cy="62" r="1.4" fill="#3b3630"/>
        <ellipse cx="123" cy="67.5" rx="2" ry="2.4" fill="#8a4a44"/>
      </g>
      <g>
        <path d="M74 132 L72 172 M86 132 L88 172" stroke="#e6e1d3" stroke-width="9"/>
        <rect x="64" y="170" width="17" height="9" rx="4" fill="#b3adc4" stroke="#8f89a4" stroke-width="1"/>
        <rect x="81" y="170" width="17" height="9" rx="4" fill="#b3adc4" stroke="#8f89a4" stroke-width="1"/>
        <polygon points="64,70 96,70 94,132 66,132" fill="#f0ece1" stroke="#b6ad98" stroke-width="1.2"/>
        <polygon points="64,70 72,70 68,131 66,131" fill="#e2dccb"/>
        <path d="M80 70 L80 130" stroke="#d4a947" stroke-width="2"/>
        <path d="M70 70 L74 78 M90 70 L86 78" stroke="#d4a947" stroke-width="1.5"/>
        <rect x="62" y="70" width="8" height="5" rx="2" fill="#d4a947"/>
        <rect x="90" y="70" width="8" height="5" rx="2" fill="#d4a947"/>
        <circle cx="76" cy="86" r="1.3" fill="#d4a947"/>
        <circle cx="76" cy="96" r="1.3" fill="#d4a947"/>
        <circle cx="76" cy="106" r="1.3" fill="#d4a947"/>
        <path d="M65 76 L52 92" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
        <circle cx="50" cy="95" r="4.5" fill="#f2c9a4"/>
        <path d="M95 76 L104 60" stroke="#f0ece1" stroke-width="9" stroke-linecap="round"/>
        <circle cx="106" cy="56" r="4.5" fill="#f2c9a4"/>
        <rect x="104" y="42" width="5.5" height="14" rx="2.5" fill="#3a3a40" transform="rotate(12 107 49)"/>
        <circle cx="105" cy="40" r="5" fill="#9aa0ad"/>
        <rect x="76" y="58" width="8" height="8" fill="#f2c9a4"/>
        <circle cx="80" cy="47" r="15" fill="#f2c9a4"/>
        <circle cx="68" cy="38" r="7" fill="#2e2a30"/>
        <circle cx="77" cy="32" r="8" fill="#2e2a30"/>
        <circle cx="88" cy="34" r="7.5" fill="#2e2a30"/>
        <circle cx="95" cy="42" r="6" fill="#2e2a30"/>
        <circle cx="65" cy="46" r="5" fill="#2e2a30"/>
        <path d="M66 44 Q66 38 74 38 Q88 36 94 44 Q90 40 80 41 Q70 40 66 44 Z" fill="#2e2a30"/>
        <circle cx="93" cy="56" r="1.4" fill="#c8ccd6"/>
        <circle cx="74" cy="48" r="1.6" fill="#3b3630"/>
        <circle cx="86" cy="48" r="1.6" fill="#3b3630"/>
        <path d="M70 43.5 Q74 41.5 77 43.5" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <path d="M83 43.5 Q86 41.5 90 43.5" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <ellipse cx="80" cy="55.5" rx="3" ry="3.8" fill="#8a3a44"/>
      </g>
    </svg>`,
  },
  {
    name: "広瀬香美",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="広瀬香美のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M64 44 Q54 60 57 112 L67 116 L66 66 Z" fill="#4a3628"/>
      <path d="M96 44 Q106 60 103 112 L93 116 L94 66 Z" fill="#4a3628"/>
      <path d="M72 136 L70 170 M88 136 L90 170" stroke="#5a5450" stroke-width="10"/>
      <rect x="61" y="166" width="19" height="17" rx="4" fill="#6b5a3e"/>
      <rect x="81" y="166" width="19" height="17" rx="4" fill="#6b5a3e"/>
      <path d="M62 169 L79 169 M82 169 L99 169" stroke="#efe9db" stroke-width="2.5"/>
      <polygon points="61,74 99,74 97,138 63,138" fill="#ebe5d7" stroke="#b9b09c" stroke-width="1.2"/>
      <path d="M62 90 Q80 96 98 90 M62 106 Q80 112 97 106 M63 122 Q80 128 97 122" stroke="#c9c0ac" stroke-width="1.8" fill="none"/>
      <path d="M70 70 Q80 78 90 70 L92 82 Q80 90 68 82 Z" fill="#d8404a"/>
      <rect x="84" y="80" width="8" height="24" rx="4" fill="#d8404a"/>
      <path d="M84 88 L92 88 M84 96 L92 96" stroke="#a32d2d" stroke-width="1.4"/>
      <path d="M64 84 L58 110" stroke="#ebe5d7" stroke-width="11" stroke-linecap="round"/>
      <circle cx="58" cy="115" r="4.5" fill="#f2c9a4"/>
      <path d="M97 78 L110 52" stroke="#ebe5d7" stroke-width="11" stroke-linecap="round"/>
      <circle cx="112" cy="47" r="5" fill="#f2c9a4"/>
      <path d="M126 26 L126 42 Q126 46 122 46 Q118 46 118 42 Q118 39 122 39 L123 39 L123 26 Z" fill="#6b6d8f"/>
      <path d="M126 26 L133 29 L133 34 L126 31 Z" fill="#6b6d8f"/>
      <path d="M138 52 L138 62 Q138 65 135.5 65 Q133 65 133 62 Q133 60 135.5 60 L136 60 L136 52 Z" fill="#8a8cab"/>
      <g stroke="#8fadd1" stroke-width="1.6" stroke-linecap="round">
        <path d="M38 40 L38 54 M31 47 L45 47 M33 42 L43 52 M43 42 L33 52"/>
      </g>
      <g stroke="#8fadd1" stroke-width="1.3" stroke-linecap="round">
        <path d="M44 96 L44 106 M39 101 L49 101 M40.5 97.5 L47.5 104.5 M47.5 97.5 L40.5 104.5"/>
      </g>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M63 52 Q60 30 80 29 Q100 30 97 52 Q92 39 80 40 Q68 39 63 52 Z" fill="#553f2e"/>
      <path d="M62 36 Q80 24 98 36" stroke="#d8404a" stroke-width="3.5" fill="none"/>
      <circle cx="63" cy="44" r="5.5" fill="#f6f2e8" stroke="#b9b09c" stroke-width="1.2"/>
      <circle cx="97" cy="44" r="5.5" fill="#f6f2e8" stroke="#b9b09c" stroke-width="1.2"/>
      <path d="M70 50 Q73 52 76 50" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M84 50 Q87 52 90 50" stroke="#3b3630" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <ellipse cx="80" cy="60" rx="4" ry="4.6" fill="#8a3a44"/>
    </svg>`,
  },
  {
    name: "女王蜂",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="女王蜂のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M62 40 Q50 62 54 170 L67 172 L64 62 Z" fill="#221f24"/>
      <path d="M98 40 Q110 62 106 170 L93 172 L96 62 Z" fill="#221f24"/>
      <polygon points="57,80 62,82 59,150" fill="#3a3444"/>
      <polygon points="103,80 98,82 101,150" fill="#3a3444"/>
      <polygon points="64,74 96,74 106,182 54,182" fill="#1d1a20"/>
      <path d="M80 74 L80 180" stroke="#d4a947" stroke-width="1.6"/>
      <path d="M56 176 L104 176" stroke="#d4a947" stroke-width="1.6"/>
      <polygon points="71,66 75,74 71,74" fill="#1d1a20"/>
      <polygon points="89,66 85,74 89,74" fill="#1d1a20"/>
      <path d="M96 80 L108 52" stroke="#1d1a20" stroke-width="8" stroke-linecap="round"/>
      <polygon points="102,60 118,68 98,72" fill="#1d1a20"/>
      <circle cx="111" cy="48" r="5" fill="#f2c9a4"/>
      <circle cx="108" cy="43.5" r="1.1" fill="#c0392b"/>
      <circle cx="111.5" cy="42.5" r="1.1" fill="#c0392b"/>
      <circle cx="114.5" cy="44.5" r="1.1" fill="#c0392b"/>
      <path d="M64 84 Q56 96 62 106" stroke="#1d1a20" stroke-width="8" fill="none" stroke-linecap="round"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M64 58 L64 66 M96 58 L96 66" stroke="#d4a947" stroke-width="1.4"/>
      <circle cx="64" cy="68" r="2" fill="#d4a947"/>
      <circle cx="96" cy="68" r="2" fill="#d4a947"/>
      <path d="M63 52 Q60 27 80 26 Q100 27 97 52 L97 44 Q97 40 92 40 L68 40 Q63 40 63 44 Z" fill="#221f24"/>
      <path d="M64 30 Q80 24 96 30 L96 45 L64 45 Z" fill="#221f24"/>
      <rect x="59" y="45" width="7" height="28" rx="3" fill="#221f24"/>
      <rect x="94" y="45" width="7" height="28" rx="3" fill="#221f24"/>
      <circle cx="73" cy="52" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="52" r="1.7" fill="#3b3630"/>
      <path d="M69 50 L66 48 M91 50 L94 48" stroke="#c0392b" stroke-width="1.4" stroke-linecap="round"/>
      <path d="M68 47 L76 47 M84 47 L92 47" stroke="#3b3630" stroke-width="1.6"/>
      <path d="M75 59 Q80 63 85 59 Q80 57.5 75 59 Z" fill="#a32d2d"/>
    </svg>`,
  },
];
