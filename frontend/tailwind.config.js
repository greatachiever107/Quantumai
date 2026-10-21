const c = (n) => `rgb(var(--${n}) / <alpha-value>)`;
module.exports = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    fontFamily: { sans: ['"Inter Variable"', "Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"] },
    colors: { bg: c("bg"), panel: c("panel"), line: c("line"), mute: c("mute"), fg: c("fg"), fg2: c("fg2"),
      up: c("up"), down: c("down"), ai: c("ai"), brand: c("brand"), warn: c("warn"), info: c("info") } } },
  plugins: [],
};
