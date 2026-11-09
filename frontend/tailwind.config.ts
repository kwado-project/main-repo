import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    container: { center: true, padding: { DEFAULT: "1rem", sm: "1.5rem", lg: "2rem" }, screens: { "2xl": "1240px" } },
    extend: {
      colors: {
        brand: { DEFAULT: "#16A34A", 50: "#F0FDF4", 100: "#DCFCE7", 200: "#BBF7D0", 300: "#86EFAC", 400: "#4ADE80", 500: "#22C55E", 600: "#16A34A", 700: "#15803D", 800: "#166534", 900: "#14532D" },
        ink: { DEFAULT: "#111827", soft: "#1F2937", deep: "#090F0B" },
        canvas: "#F7FAF7",
        muted: "#64748B",
        line: "#E5E7EB",
        gold: "#F5B400",
        flame: "#FB923C",
      },
      fontFamily: { sans: ['"Plus Jakarta Sans Variable"', "ui-sans-serif", "system-ui", "sans-serif"] },
      borderRadius: { xl: "0.875rem", "2xl": "1.125rem", "3xl": "1.5rem" },
      boxShadow: {
        card: "0 1px 2px rgba(17,24,39,.04), 0 4px 16px -4px rgba(17,24,39,.06)",
        lift: "0 10px 30px -10px rgba(17,24,39,.18)",
        glow: "0 0 0 1px rgba(22,163,74,.25), 0 8px 30px -8px rgba(22,163,74,.45)",
        press: "inset 0 -3px 0 rgba(0,0,0,.18)",
      },
      keyframes: {
        float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-8px)" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
        flicker: { "0%,100%": { transform: "scale(1) rotate(-2deg)" }, "50%": { transform: "scale(1.08) rotate(2deg)" } },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        shimmer: "shimmer 1.6s infinite",
        flicker: "flicker 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
