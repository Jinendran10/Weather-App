/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        sky: {
          950: '#0b1e35',
        },
      },
    },
  },
  plugins: [],
}
