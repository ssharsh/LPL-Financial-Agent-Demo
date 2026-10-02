/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // LPL-ish brand palette
        brand: {
          DEFAULT: "#0b5c3f",
          light: "#13a06b",
          dark: "#083f2b",
        },
        // Faint brand-green surface tint for light panels/bands (accent, not fill)
        surface: {
          tint: "#f3f8f5",
        },
      },
      boxShadow: {
        // Soft, airy elevation for the light premium shell
        soft: "0 1px 2px rgba(16, 24, 40, 0.04), 0 4px 12px rgba(16, 24, 40, 0.06)",
      },
      keyframes: {
        "message-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "message-in": "message-in 0.28s ease-out both",
      },
    },
  },
  plugins: [],
};
