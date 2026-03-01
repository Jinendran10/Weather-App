/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary:     '#2563EB',  // buttons, active states
        secondary:   '#38BDF8',  // hover, links, icons
        'app-bg':    '#F1F5F9',  // page background
        'app-card':  '#FFFFFF',  // card background
        'text-main': '#0F172A',  // headings, primary text
        'text-sec':  '#475569',  // secondary labels
        'temp-acc':  '#F97316',  // temperature numbers
      },
    },
  },
  plugins: [],
}
