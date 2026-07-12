import type { ProfileArtist } from "./types";

// Popタイプの有名人イラスト（docs/62 §8-1 確定版）。
// 実在アーティストの写真は使わず、特徴記号を抽象化した自前のフラットイラスト。
// 白物はアイボリー＋輪郭線で背景から分離する規律（docs/62 §5-2）適用済み。

export const POP_ARTISTS: ProfileArtist[] = [
  {
    name: "いきものがかり",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="いきものがかりの3人のイラスト">
      <ellipse cx="80" cy="188" rx="62" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M23 134 L21 166 M29 134 L31 166" stroke="#2c2c30" stroke-width="6"/>
        <rect x="15" y="164" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="26" y="164" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="17,90 35,90 34,136 18,136" fill="#7a6a52"/>
        <path d="M30 104 L14 88" stroke="#4a3320" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="32" cy="112" rx="12" ry="10" fill="#c08a4a"/>
        <ellipse cx="32" cy="112" rx="5" ry="4" fill="#7a4e26"/>
        <path d="M18 90 L12 96" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="11" cy="98" r="4" fill="#f2c9a4"/>
        <path d="M34 90 L36 100" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="37" cy="103" r="4" fill="#f2c9a4"/>
        <rect x="23" y="72" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="26" cy="64" r="10" fill="#f2c9a4"/>
        <path d="M16 62 Q15 50 26 49 Q37 50 36 62 Q32 55 26 56 Q20 55 16 62 Z" fill="#3a2e26"/>
        <circle cx="22" cy="64" r="1.3" fill="#3b3630"/>
        <circle cx="30" cy="64" r="1.3" fill="#3b3630"/>
        <path d="M23 69 Q26 71 29 69" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M131 134 L129 166 M137 134 L139 166" stroke="#2c2c30" stroke-width="6"/>
        <rect x="123" y="164" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="134" y="164" width="13" height="7" rx="3.5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <polygon points="125,90 143,90 142,136 126,136" fill="#5c6a58"/>
        <path d="M130 104 L146 88" stroke="#4a3320" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="128" cy="112" rx="12" ry="10" fill="#c08a4a"/>
        <ellipse cx="128" cy="112" rx="5" ry="4" fill="#7a4e26"/>
        <path d="M126 90 L124 100" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="123" cy="103" r="4" fill="#f2c9a4"/>
        <path d="M142 90 L148 96" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="149" cy="98" r="4" fill="#f2c9a4"/>
        <rect x="131" y="72" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="134" cy="64" r="10" fill="#f2c9a4"/>
        <path d="M124 58 Q124 46 134 47 Q145 46 145 60 L142 62 L142 54 L126 54 Z" fill="#3a2e26"/>
        <path d="M122 58 L146 58 L145 52 Q134 47 124 52 Z" fill="#33302c"/>
        <path d="M123 55 L145 55" stroke="#6b5a3e" stroke-width="2"/>
        <circle cx="130" cy="64" r="1.3" fill="#3b3630"/>
        <circle cx="138" cy="64" r="1.3" fill="#3b3630"/>
        <ellipse cx="134" cy="69.5" rx="1.8" ry="2.2" fill="#8a4a44"/>
      </g>
      <g>
        <path d="M74 138 L72 172 M86 138 L88 172" stroke="#f2c9a4" stroke-width="8"/>
        <rect x="63" y="168" width="18" height="11" rx="5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <rect x="80" y="168" width="18" height="11" rx="5" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
        <path d="M63 176 L80 176 M80 176 L98 176" stroke="#b9b2a2" stroke-width="1.5"/>
        <polygon points="65,74 95,74 101,138 59,138" fill="#7fc4d8"/>
        <polygon points="65,74 78,74 71,112" fill="#a3d8e6"/>
        <path d="M62 122 L98 122" stroke="#5a9db0" stroke-width="2.5"/>
        <circle cx="80" cy="94" r="2.4" fill="#e8f4f8"/>
        <circle cx="72" cy="108" r="2.4" fill="#e8f4f8"/>
        <circle cx="88" cy="108" r="2.4" fill="#e8f4f8"/>
        <path d="M95 78 L108 58" stroke="#7fc4d8" stroke-width="9" stroke-linecap="round"/>
        <circle cx="110" cy="55" r="4.5" fill="#f2c9a4"/>
        <path d="M65 80 L58 100" stroke="#7fc4d8" stroke-width="9" stroke-linecap="round"/>
        <circle cx="57" cy="103" r="4.5" fill="#f2c9a4"/>
        <rect x="54" y="105" width="6" height="15" rx="3" fill="#3a3a40"/>
        <circle cx="57" cy="123" r="5.5" fill="#9aa0ad"/>
        <rect x="76" y="60" width="8" height="8" fill="#f2c9a4"/>
        <circle cx="80" cy="48" r="15" fill="#f2c9a4"/>
        <path d="M63 50 Q60 30 80 29 Q100 30 97 50 L94 62 Q95 42 80 42 Q65 42 66 62 L63 50 Z" fill="#5c4030"/>
        <polygon points="68,34 78,31 71,42" fill="#755440"/>
        <circle cx="73" cy="49" r="1.7" fill="#3b3630"/>
        <circle cx="87" cy="49" r="1.7" fill="#3b3630"/>
        <path d="M69 45 Q73 43 76 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <path d="M84 45 Q87 43 91 45" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <path d="M75 57 Q80 61 85 57" stroke="#c05a70" stroke-width="2" fill="none" stroke-linecap="round"/>
        <ellipse cx="80" cy="53" rx="2.6" ry="3.2" fill="#8a4a44"/>
      </g>
    </svg>`,
  },
  {
    name: "北村匠海",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="北村匠海のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#2c2c30" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#2c2c30"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#2c2c30"/>
      <polygon points="58,76 102,76 99,136 61,136" fill="#c9b48f"/>
      <polygon points="66,74 94,74 92,120 68,120" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1"/>
      <polygon points="66,74 74,74 70,118" fill="#e2dccb"/>
      <path d="M80 76 L80 118" stroke="#d8d1bf" stroke-width="1.2"/>
      <path d="M61 82 L54 108" stroke="#c9b48f" stroke-width="9" stroke-linecap="round"/>
      <circle cx="53" cy="112" r="5" fill="#f2c9a4"/>
      <path d="M99 82 L100 100" stroke="#c9b48f" stroke-width="9" stroke-linecap="round"/>
      <circle cx="100" cy="104" r="5" fill="#f2c9a4"/>
      <rect x="97" y="106" width="6" height="16" rx="3" fill="#3a3a40"/>
      <circle cx="100" cy="124" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 28 80 27 Q101 28 98 52 L94 54 Q95 38 80 38 Q65 38 66 54 Z" fill="#1f1c22"/>
      <path d="M80 32 L72 52 M80 32 L88 52" stroke="#2c282e" stroke-width="4"/>
      <path d="M74 51 L70 49 M86 51 L90 49" stroke="#2c282e" stroke-width="4" stroke-linecap="round"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M76 58 Q80 60 84 58" stroke="#8a4a44" stroke-width="1.7" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "aiko",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="aikoのイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M63 44 Q54 58 58 82 L68 84 L66 62 Z" fill="#2e2a2a"/>
      <path d="M97 44 Q106 58 102 82 L92 84 L94 62 Z" fill="#2e2a2a"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#f2c9a4" stroke-width="8"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#efe6de" stroke="#c2baa8" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#efe6de" stroke="#c2baa8" stroke-width="1"/>
      <polygon points="64,74 96,74 102,136 58,136" fill="#f08a72"/>
      <polygon points="64,74 78,74 71,112" fill="#f6a894"/>
      <path d="M60 124 L100 124" stroke="#d46a54" stroke-width="2.5"/>
      <circle cx="80" cy="98" r="3" fill="#fbe0d6"/>
      <path d="M64 80 L56 104" stroke="#f08a72" stroke-width="8" stroke-linecap="round"/>
      <circle cx="55" cy="107" r="4.5" fill="#f2c9a4"/>
      <path d="M96 80 L104 104" stroke="#f08a72" stroke-width="8" stroke-linecap="round"/>
      <circle cx="105" cy="107" r="4.5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M60 54 Q57 30 80 29 Q103 30 100 54 L98 62 Q98 48 92 46 L68 46 Q62 48 62 62 Z" fill="#2e2a2a"/>
      <path d="M62 42 Q80 36 98 42 L98 47 Q80 42 62 47 Z" fill="#2e2a2a"/>
      <path d="M69 51 Q72.5 48 76 51" stroke="#3b3630" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="M84 51 Q87.5 48 91 51" stroke="#3b3630" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="68" cy="57" rx="2.8" ry="1.7" fill="#f2a892"/>
      <ellipse cx="92" cy="57" rx="2.8" ry="1.7" fill="#f2a892"/>
      <path d="M74 58 Q80 64 86 58 Q80 62 74 58 Z" fill="#c95a5a"/>
    </svg>`,
  },
  {
    name: "花村想太（Da-iCE）",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="花村想太のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#26242a" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#f4f1e9" stroke="#bcb5a4" stroke-width="1"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#2e2c34"/>
      <path d="M68 88 Q80 94 92 88" stroke="#8f95a8" stroke-width="1.6" fill="none"/>
      <path d="M72 90 L74 98 M88 90 L86 98" stroke="#9aa0ad" stroke-width="1.4"/>
      <circle cx="80" cy="102" r="2.2" fill="#c8ccd6"/>
      <path d="M63 80 L54 100" stroke="#2e2c34" stroke-width="9" stroke-linecap="round"/>
      <circle cx="52" cy="103" r="5" fill="#f2c9a4"/>
      <path d="M97 82 L100 66" stroke="#2e2c34" stroke-width="9" stroke-linecap="round"/>
      <circle cx="101" cy="63" r="5" fill="#f2c9a4"/>
      <rect x="98" y="46" width="6" height="17" rx="3" fill="#3a3a40" transform="rotate(-12 101 54)"/>
      <circle cx="97" cy="44" r="5.5" fill="#9aa0ad"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 52 Q59 28 80 27 Q101 28 98 52 Q93 37 80 38 Q67 37 62 52 Z" fill="#2b2830"/>
      <path d="M66 42 Q76 38 86 42" stroke="#6b7086" stroke-width="2.2" fill="none"/>
      <polygon points="70,34 79,31 73,41" fill="#4a4f60"/>
      <circle cx="73" cy="51" r="1.7" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.7" fill="#3b3630"/>
      <path d="M69 46 Q73 44 76 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <path d="M84 46 Q87 44 91 46" stroke="#3b3630" stroke-width="1.4" fill="none"/>
      <ellipse cx="80" cy="59" rx="3" ry="3.6" fill="#7d3b3b"/>
    </svg>`,
  },
  {
    name: "SHISHAMO",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="SHISHAMOの3人のイラスト">
      <ellipse cx="80" cy="188" rx="62" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M23 132 L21 164 M29 132 L31 164" stroke="#3a3540" stroke-width="6"/>
        <rect x="15" y="162" width="13" height="7" rx="3.5" fill="#2c2c30"/>
        <rect x="26" y="162" width="13" height="7" rx="3.5" fill="#2c2c30"/>
        <polygon points="17,88 35,88 34,134 18,134" fill="#6b6478"/>
        <path d="M30 102 L14 86" stroke="#3a2e26" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="30" cy="110" rx="10" ry="16" fill="#3a3444"/>
        <path d="M18 88 L12 94" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="11" cy="96" r="4" fill="#f2c9a4"/>
        <path d="M34 88 L36 98" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <circle cx="37" cy="101" r="4" fill="#f2c9a4"/>
        <rect x="23" y="70" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="26" cy="62" r="10" fill="#f2c9a4"/>
        <path d="M15 62 Q14 48 26 47 Q38 48 37 62 L34 66 L35 54 Q26 50 17 54 L18 66 Z" fill="#2e2a2a"/>
        <circle cx="22" cy="62" r="1.3" fill="#3b3630"/>
        <circle cx="30" cy="62" r="1.3" fill="#3b3630"/>
        <path d="M23 67 Q26 69 29 67" stroke="#8a4a44" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M131 132 L129 164 M137 132 L139 164" stroke="#3a3540" stroke-width="6"/>
        <rect x="123" y="162" width="13" height="7" rx="3.5" fill="#2c2c30"/>
        <rect x="134" y="162" width="13" height="7" rx="3.5" fill="#2c2c30"/>
        <polygon points="125,88 143,88 142,134 126,134" fill="#6b6478"/>
        <path d="M130 102 L146 86" stroke="#3a2e26" stroke-width="4" stroke-linecap="round"/>
        <rect x="120" y="104" width="26" height="10" rx="2" fill="#2c2c30"/>
        <path d="M124 104 L124 112 M129 104 L129 112 M134 104 L134 112 M139 104 L139 112" stroke="#f2f0ea" stroke-width="2.4"/>
        <path d="M126 88 L124 98" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <path d="M142 88 L148 94" stroke="#f2c9a4" stroke-width="6" stroke-linecap="round"/>
        <rect x="131" y="70" width="6" height="8" fill="#f2c9a4"/>
        <circle cx="134" cy="62" r="10" fill="#f2c9a4"/>
        <path d="M123 62 Q122 48 134 47 Q146 48 145 62 L142 66 L143 54 Q134 50 125 54 L126 66 Z" fill="#2e2a2a"/>
        <circle cx="130" cy="62" r="1.3" fill="#3b3630"/>
        <circle cx="138" cy="62" r="1.3" fill="#3b3630"/>
        <ellipse cx="134" cy="67.5" rx="1.8" ry="2.2" fill="#8a4a44"/>
      </g>
      <g>
        <path d="M74 134 L72 170 M86 134 L88 170" stroke="#3a3540" stroke-width="9"/>
        <rect x="64" y="168" width="17" height="9" rx="4" fill="#2c2c30"/>
        <rect x="81" y="168" width="17" height="9" rx="4" fill="#2c2c30"/>
        <polygon points="64,72 96,72 94,134 66,134" fill="#5c5568"/>
        <path d="M66 74 L94 108" stroke="#5a9db0" stroke-width="4"/>
        <ellipse cx="96" cy="112" rx="16" ry="12" fill="#7fc4d8"/>
        <path d="M99 108 L127 78" stroke="#4a3320" stroke-width="5" stroke-linecap="round"/>
        <rect x="124" y="72" width="9" height="9" rx="2" fill="#2c2420"/>
        <path d="M94 106 L66 82" stroke="#a3d8e6" stroke-width="0.8"/>
        <path d="M88 106 L86 122 M96 108 L96 124 M104 106 L106 122" stroke="#5a9db0" stroke-width="2"/>
        <path d="M65 78 L52 94" stroke="#5c5568" stroke-width="9" stroke-linecap="round"/>
        <circle cx="50" cy="97" r="4.5" fill="#f2c9a4"/>
        <path d="M95 76 L98 92" stroke="#5c5568" stroke-width="9" stroke-linecap="round"/>
        <circle cx="99" cy="95" r="4.5" fill="#f2c9a4"/>
        <rect x="76" y="60" width="8" height="8" fill="#f2c9a4"/>
        <circle cx="80" cy="49" r="15" fill="#f2c9a4"/>
        <path d="M64 52 Q61 30 80 29 Q99 30 96 52 L93 56 L94 44 Q80 40 66 44 L67 56 Z" fill="#221f22"/>
        <polygon points="68,35 78,32 72,42" fill="#3a3538"/>
        <circle cx="74" cy="49" r="1.6" fill="#3b3630"/>
        <circle cx="86" cy="49" r="1.6" fill="#3b3630"/>
        <path d="M70 44 Q74 42 77 44" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <path d="M83 44 Q86 42 90 44" stroke="#3b3630" stroke-width="1.4" fill="none"/>
        <path d="M75 56 Q80 60 85 56" stroke="#c05a70" stroke-width="2" fill="none" stroke-linecap="round"/>
      </g>
    </svg>`,
  },
  {
    name: "マカロニえんぴつ",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="マカロニえんぴつ（はっとり）のイラスト">
      <ellipse cx="80" cy="190" rx="40" ry="6" fill="#dcdce3"/>
      <path d="M72 134 L70 176 M88 134 L90 176" stroke="#3a3138" stroke-width="10"/>
      <rect x="61" y="174" width="19" height="9" rx="4" fill="#2c2c30"/>
      <rect x="81" y="174" width="19" height="9" rx="4" fill="#2c2c30"/>
      <polygon points="60,74 100,74 97,136 63,136" fill="#d9a83e"/>
      <polygon points="60,74 74,74 68,120" fill="#e6bd5c"/>
      <path d="M68 74 L72 82 M92 74 L88 82" stroke="#b58a26" stroke-width="1.5"/>
      <circle cx="80" cy="94" r="1.6" fill="#b58a26"/>
      <circle cx="80" cy="106" r="1.6" fill="#b58a26"/>
      <circle cx="80" cy="118" r="1.6" fill="#b58a26"/>
      <path d="M66 78 L92 112" stroke="#8a5a2e" stroke-width="4"/>
      <path d="M94 104 L122 76" stroke="#8a5a2e" stroke-width="5" stroke-linecap="round"/>
      <rect x="119" y="70" width="9" height="9" rx="2" fill="#4a3320"/>
      <ellipse cx="92" cy="114" rx="16" ry="13" fill="#c08a4a"/>
      <ellipse cx="92" cy="114" rx="6.5" ry="5.5" fill="#7a4e26"/>
      <path d="M92 108 L66 84" stroke="#e8d9c0" stroke-width="0.8"/>
      <path d="M63 80 L58 106" stroke="#d9a83e" stroke-width="9" stroke-linecap="round"/>
      <circle cx="57" cy="110" r="5" fill="#f2c9a4"/>
      <rect x="76" y="62" width="8" height="8" fill="#f2c9a4"/>
      <circle cx="80" cy="50" r="16" fill="#f2c9a4"/>
      <path d="M62 50 Q59 28 80 27 Q101 28 98 50 Q93 36 80 37 Q67 36 62 50 Z" fill="#2e2820"/>
      <polygon points="68,33 78,30 71,41" fill="#453c30"/>
      <circle cx="73" cy="51" r="4.6" fill="none" stroke="#c95a4a" stroke-width="1.8"/>
      <circle cx="87" cy="51" r="4.6" fill="none" stroke="#c95a4a" stroke-width="1.8"/>
      <path d="M77.5 51 L82.5 51" stroke="#c95a4a" stroke-width="1.6"/>
      <path d="M68.4 49 L64 47 M91.6 49 L96 47" stroke="#c95a4a" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="73" cy="51" r="1.6" fill="#3b3630"/>
      <circle cx="87" cy="51" r="1.6" fill="#3b3630"/>
      <path d="M70 57 Q80 60 90 57" stroke="#4a3b2e" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <path d="M76 61 Q80 63 84 61" stroke="#8a4a44" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </svg>`,
  },
  {
    name: "Every Little Thing",
    svg: `<svg viewBox="0 0 160 200" role="img" aria-label="Every Little Thing（持田香織と伊藤一朗）のイラスト">
      <ellipse cx="80" cy="188" rx="52" ry="6" fill="#dcdce3"/>
      <g>
        <path d="M106 134 L104 172 M118 134 L120 172" stroke="#2c2c30" stroke-width="8"/>
        <rect x="97" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <rect x="111" y="170" width="16" height="8" rx="4" fill="#2c2c30"/>
        <polygon points="100,78 124,78 122,136 102,136" fill="#4a4650"/>
        <path d="M104 100 L128 82" stroke="#4a3320" stroke-width="4.5" stroke-linecap="round"/>
        <rect x="126" y="74" width="9" height="9" rx="2" fill="#2c2420"/>
        <ellipse cx="102" cy="112" rx="14" ry="11" fill="#b5793f"/>
        <ellipse cx="102" cy="112" rx="6" ry="5" fill="#7a4e26"/>
        <path d="M104 106 L128 88" stroke="#e8d9c0" stroke-width="0.8"/>
        <path d="M102 84 L101 100" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
        <circle cx="100" cy="103" r="4.5" fill="#f2c9a4"/>
        <path d="M122 82 L124 68" stroke="#f2c9a4" stroke-width="7" stroke-linecap="round"/>
        <circle cx="125" cy="65" r="4.5" fill="#f2c9a4"/>
        <rect x="107" y="65" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="110" cy="56" r="13" fill="#f2c9a4"/>
        <path d="M97 56 Q96 40 110 39 Q124 40 123 56 Q124 74 120 90 L116 88 Q120 72 118 56 Q116 46 110 46 Q104 46 102 56 Q100 72 104 88 L100 90 Q96 74 97 56 Z" fill="#2e2a28"/>
        <circle cx="106" cy="57" r="1.5" fill="#3b3630"/>
        <circle cx="116" cy="57" r="1.5" fill="#3b3630"/>
        <path d="M102 52 Q106 50 109 52 M113 52 Q116 50 120 52" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <path d="M107 63 Q110 65 113 63" stroke="#8a4a44" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
      <g>
        <path d="M42 134 L40 172 M52 134 L54 172" stroke="#f2c9a4" stroke-width="8"/>
        <rect x="33" y="170" width="16" height="8" rx="4" fill="#efe6de" stroke="#c2baa8" stroke-width="1"/>
        <rect x="47" y="170" width="16" height="8" rx="4" fill="#efe6de" stroke="#c2baa8" stroke-width="1"/>
        <polygon points="34,76 60,76 58,136 36,136" fill="#f0ece1" stroke="#bcb5a4" stroke-width="1.2"/>
        <polygon points="34,76 43,76 39,135" fill="#e2dccb"/>
        <path d="M47 76 L47 134" stroke="#d8d1bf" stroke-width="1.2"/>
        <path d="M36 84 Q30 96 36 108" stroke="#f0ece1" stroke-width="8" stroke-linecap="round" fill="none"/>
        <circle cx="37" cy="110" r="4.5" fill="#f2c9a4"/>
        <rect x="34" y="112" width="6" height="14" rx="3" fill="#3a3a40"/>
        <circle cx="37" cy="129" r="5.5" fill="#9aa0ad"/>
        <path d="M58 84 Q64 96 58 108" stroke="#f0ece1" stroke-width="8" stroke-linecap="round" fill="none"/>
        <circle cx="57" cy="110" r="4.5" fill="#f2c9a4"/>
        <rect x="54" y="112" width="6" height="14" rx="3" fill="#3a3a40"/>
        <circle cx="57" cy="129" r="5.5" fill="#9aa0ad"/>
        <rect x="43" y="65" width="7" height="8" fill="#f2c9a4"/>
        <circle cx="46" cy="56" r="13" fill="#f2c9a4"/>
        <path d="M33 56 Q32 40 46 39 Q60 40 59 56 Q56 44 46 45 Q36 44 33 56 Z" fill="#4a3628"/>
        <polygon points="38,42 47,39 41,48" fill="#5c4636"/>
        <circle cx="41.5" cy="56" r="1.5" fill="#3b3630"/>
        <circle cx="50.5" cy="56" r="1.5" fill="#3b3630"/>
        <path d="M38 52 Q41 50 44 52 M48 52 Q51 50 54 52" stroke="#3b3630" stroke-width="1.3" fill="none"/>
        <ellipse cx="46" cy="63" rx="2.8" ry="3.4" fill="#8a3a44"/>
      </g>
    </svg>`,
  },
];
