/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["DM Sans", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono:    ["JetBrains Mono", "Courier New", "monospace"],
        display: ["Syne", "DM Sans", "sans-serif"],
      },
      colors: {
        bg:       "#080808",
        surface:  "#0e0e0e",
        panel:    "#141414",
        raised:   "#1a1a1a",
        border:   "#222222",
        dim:      "#2a2a2a",
        muted:    "#555555",
        subtle:   "#888888",
        gold:     "#f5a623",
        "gold-dim": "#7a5010",
        "gold-bg":  "#1c1200",
        green:    "#22c55e",
        red:      "#ef4444",
        blue:     "#3b82f6",
        yellow:   "#eab308",
      },
      animation: {
        "fade-in":    "fadeIn 0.3s ease forwards",
        "slide-up":   "slideUp 0.3s ease forwards",
        "pulse-slow": "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
      },
      keyframes: {
        fadeIn:  { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
