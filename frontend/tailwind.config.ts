import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        maroon: "#8A1538",
        "maroon-dark": "#64102A",
        sand: "#F4EEE6",
        ink: "#1F2328",
        muted: "#6B7280",
        line: "#E7E2DA",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(31, 35, 40, 0.06), 0 8px 24px rgba(31, 35, 40, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
