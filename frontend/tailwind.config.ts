import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#f0f4fa", 100: "#dce6f2", 200: "#c0d2e8", 300: "#94b3d6",
          400: "#628bbc", 500: "#406ea3", 600: "#2f5587", 700: "#28456e",
          800: "#1d3453", 900: "#152640",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(15 33 60 / 0.05)",
        pop: "0 8px 24px -8px rgb(15 33 60 / 0.18)",
      },
    },
  },
  plugins: [],
};
export default config;
