import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        coffee: {
          bg: "#f5f1ea",
          ink: "#2b211a",
          accent: "#6f4e37",
        },
      },
    },
  },
  plugins: [],
};

export default config;
