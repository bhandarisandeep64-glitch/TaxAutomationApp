/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
            950: '#020617', // Custom dark color for the theme
        }
      }
    },
  },
  plugins: [],
}