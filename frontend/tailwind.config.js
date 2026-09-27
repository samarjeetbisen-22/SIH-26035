/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        metro: {
          blue: '#2563EB',
          'blue-dark': '#1D4ED8',
          'blue-light': '#EFF6FF',
          slate: '#0F172A',
          muted: '#64748B',
          lightmuted: '#94A3B8',
          bg: '#F8FAFC',
          card: '#FFFFFF',
          border: '#E2E8F0',
          pass: '#059669',
          'pass-bg': '#ECFDF5',
          fail: '#DC2626',
          'fail-bg': '#FEF2F2',
          warn: '#D97706',
          'warn-bg': '#FFFBEB'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02)',
        'paper': '0 1px 4px 0 rgba(15, 23, 42, 0.06), 0 0 1px 1px rgba(15, 23, 42, 0.04)'
      }
    },
  },
  plugins: [],
}
