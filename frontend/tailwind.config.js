/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,vue}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Nunito"', 'ui-sans-serif', 'system-ui'],
      },
      colors: {
        brand: {
          50: '#f2f7f1',
          100: '#e5efe3',
          200: '#c8e1c4',
          300: '#9fcb97',
          400: '#7eb872',
          500: '#6aa655',
          600: '#568a45',
          700: '#456d38',
          800: '#38572e',
          900: '#2e4726',
        },
        ink: '#0f172a',
        slate: {
          25: '#f9fafb',
          950: '#0b1020',
        },
      },
      boxShadow: {
        soft: '0 20px 40px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
}
