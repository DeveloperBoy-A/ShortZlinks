import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0B1020",
        card: "#111831",
        card2: "#0F172A",
        primary: "#7C3AED",
        secondary: "#06B6D4",
        accent: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        muted: "#94A3B8",
        border: "rgba(148,163,184,0.16)"
      },
      boxShadow: {
        glow: "0 10px 30px rgba(124,58,237,0.25)",
        soft: "0 10px 30px rgba(2,8,23,0.35)"
      },
      backgroundImage: {
        hero:
          "radial-gradient(circle at top left, rgba(124,58,237,.25), transparent 25%), radial-gradient(circle at top right, rgba(6,182,212,.22), transparent 25%), linear-gradient(180deg, #0b1020 0%, #0b1224 100%)"
      },
      borderRadius: {
        xl2: "1.25rem"
      },
      keyframes: {
        floaty: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" }
        },
        shine: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" }
        },
        marqueeGlow: {
          "0%,100%": { opacity: "0.85" },
          "50%": { opacity: "1" }
        }
      },
      animation: {
        floaty: "floaty 4s ease-in-out infinite",
        shine: "shine 8s linear infinite",
        marqueeGlow: "marqueeGlow 2.5s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;