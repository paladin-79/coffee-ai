import type { Config } from "tailwindcss";

// Design tokens — Vietnamese enamel signboard.
//
// The ground is a saturated enamel green, not a neutral near-black, and the
// cream that used to be the page background is now the *type* colour. The app
// is read in two places at once: a phone held in the hand and a projector in
// the room, so nothing that carries meaning is set below 15px and every
// foreground pair below clears WCAG AA. Measured, not estimated:
//
//   milk on enamel                13.35:1
//   milk on enamel.raised         11.04:1   (AI bubble)
//   enamel on milk                13.35:1   (player bubble)
//   milk.dim on enamel             7.32:1
//   milk.dim on enamel.raised      6.05:1
//   signal.bright on signal.wash   7.92:1
//   caramel on enamel              5.23:1
//   enamel on caramel              5.23:1   (button label)
//   enamel on caramel.lift         6.47:1   (button label, hover)
//
// caramel.lift is *lighter* than caramel, not darker. The first pass used a
// darker hover (#a9682c) which dropped the dark button label to 3.38:1 —
// hovering the primary action made it harder to read. Brightening on hover
// raises the ratio instead.
//
// Two colours are deliberately never used as text: `signal` (3.10:1 on the
// enamel ground) is for borders and fills only, with `signal.bright` carrying
// the words; `milk` is never set on `caramel` (2.55:1).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        enamel: {
          DEFAULT: "#0d2b26",
          raised: "#143a33",
          edge: "#1d4b42",
        },
        milk: {
          DEFAULT: "#f4f1e6",
          dim: "#a9b8b2",
        },
        caramel: {
          DEFAULT: "#d2873f",
          lift: "#e09b58",
        },
        signal: {
          DEFAULT: "#d7362b",
          bright: "#ff9385",
          wash: "#2e1512",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      // Major third (1.25) — 13 / 15 / 17 / 20 / 26 / 38 / 56.
      // Body is 17px, not the usual 14px: it has to survive both a phone at
      // arm's length and a projected wall.
      fontSize: {
        micro: ["0.8125rem", { lineHeight: "1.45" }],
        small: ["0.9375rem", { lineHeight: "1.5" }],
        base: ["1.0625rem", { lineHeight: "1.6" }],
        lead: ["1.25rem", { lineHeight: "1.5" }],
        title: ["1.625rem", { lineHeight: "1.25" }],
        hero: ["2.375rem", { lineHeight: "1.05" }],
        mega: ["3.5rem", { lineHeight: "0.98" }],
      },
      maxWidth: {
        measure: "34rem",
      },
    },
  },
  plugins: [],
};

export default config;
