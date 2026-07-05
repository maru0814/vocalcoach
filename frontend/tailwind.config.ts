import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        rounded: [
          "var(--font-rounded)",
          "Hiragino Maru Gothic ProN",
          "ui-rounded",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        brand: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
        },
        // ステージの闇（ヒーロー/最終CTA/診断セクション専用）docs/55 §5-1
        night: {
          800: "#1e1655",
          900: "#171045",
          950: "#0f0a2e",
        },
        // ネオン装飾色。テキストには使わない（docs/55 §5-7）
        neon: {
          cyan: "#22d3ee",
          pink: "#f472b6",
          amber: "#fbbf24",
        },
      },
      boxShadow: {
        soft: "0 10px 40px -12px rgba(124, 58, 237, 0.25)",
        card: "0 8px 30px -10px rgba(30, 41, 59, 0.18)",
        glow: "0 0 0 4px rgba(139, 92, 246, 0.15)",
        "card-2": "0 2px 8px -2px rgba(30, 41, 59, 0.08), 0 20px 50px -20px rgba(76, 29, 149, 0.30)",
        "glow-neon": "0 0 28px -6px rgba(34, 211, 238, 0.5)",
        "glow-spot": "0 0 80px -10px rgba(251, 191, 36, 0.35)",
      },
      keyframes: {
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        floaty: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
        bounceDot: {
          "0%,80%,100%": { transform: "scale(0.6)", opacity: "0.4" },
          "40%": { transform: "scale(1)", opacity: "1" },
        },
        pulseRing: {
          "0%": { transform: "scale(0.9)", opacity: "0.7" },
          "70%": { transform: "scale(1.6)", opacity: "0" },
          "100%": { opacity: "0" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        growBar: {
          "0%": { width: "0%" },
        },
        eq: {
          "0%,100%": { transform: "scaleY(0.25)" },
          "50%": { transform: "scaleY(1)" },
        },
        popIn: {
          "0%": { opacity: "0", transform: "translateY(10px) scale(0.96)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        twinkle: {
          "0%,100%": { opacity: "0.2" },
          "50%": { opacity: "0.9" },
        },
        noteFloat: {
          "0%": { transform: "translateY(0)", opacity: "0" },
          "20%": { opacity: "0.5" },
          "100%": { transform: "translateY(-90px)", opacity: "0" },
        },
      },
      animation: {
        "fade-in-up": "fadeInUp 0.4s ease-out both",
        floaty: "floaty 4s ease-in-out infinite",
        "bounce-dot": "bounceDot 1.2s infinite ease-in-out",
        "pulse-ring": "pulseRing 1.5s cubic-bezier(0.2,0.6,0.4,1) infinite",
        "grow-bar": "growBar 0.8s ease-out",
        eq: "eq 0.8s ease-in-out infinite",
        "pop-in": "popIn 0.45s cubic-bezier(0.2,0.8,0.3,1) both",
        twinkle: "twinkle 2.4s ease-in-out infinite",
        "note-float": "noteFloat 5s ease-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
