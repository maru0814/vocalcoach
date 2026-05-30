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
      },
      boxShadow: {
        soft: "0 10px 40px -12px rgba(124, 58, 237, 0.25)",
        card: "0 8px 30px -10px rgba(30, 41, 59, 0.18)",
        glow: "0 0 0 4px rgba(139, 92, 246, 0.15)",
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
      },
      animation: {
        "fade-in-up": "fadeInUp 0.4s ease-out both",
        floaty: "floaty 4s ease-in-out infinite",
        "bounce-dot": "bounceDot 1.2s infinite ease-in-out",
        "pulse-ring": "pulseRing 1.5s cubic-bezier(0.2,0.6,0.4,1) infinite",
        "grow-bar": "growBar 0.8s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
