/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#627d98',
          500: '#1a3a6e', // Main primary - SRCC Navy Blue
          600: '#153058',
          700: '#102647',
          800: '#0b1c36',
          900: '#061224',
        },
        secondary: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#d4a827', // SRCC Gold
          500: '#c49a1a',
          600: '#a78316',
          700: '#8a6c12',
          800: '#6d550e',
          900: '#503e0a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'medium': '0 8px 20px rgba(29, 33, 43, 0.08)',
        'large': '0 20px 40px rgba(28, 24, 21, 0.12)',
      },
    },
  },
  plugins: [
    require('tailwindcss-animate'),
    require('tailwindcss-react-aria-components'),
  ],
}

