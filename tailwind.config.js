/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/app.js"],
  theme: {
    extend: {
      colors: {
        ink: "#13262B",
        fog: "#EFF3F0",
        paper: "#FBFCFA",
        line: "#D5DDD9",
        river: {
          50: "#EAF3F2",
          100: "#D6E8E7",
          600: "#1F7480",
          700: "#17606B",
          800: "#0E3F47",
          900: "#0A2E35",
        },
        maize: { DEFAULT: "#E0A526", dark: "#7A5600" },
        clay: "#B5482B",
        risk: { bajo: "#4F8A6B", moderado: "#D9A21B", alto: "#D9722B", critico: "#B3261E" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Public Sans Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
