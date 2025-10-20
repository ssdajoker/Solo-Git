/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        heaven: {
          bg: {
            primary: '#0A0E1A',
            secondary: '#0D1117',
            tertiary: '#1A1F2E',
            hover: '#252A3A',
            active: '#2D3348',
          },
          blue: {
            primary: '#3B82F6',
            hover: '#2563EB',
          },
          accent: {
            orange: '#F97316',
            green: '#22C55E',
            cyan: '#06B6D4',
            purple: '#A855F7',
            pink: '#EC4899',
            red: '#EF4444',
          },
          text: {
            primary: '#FFFFFF',
            secondary: '#9CA3AF',
            tertiary: '#6B7280',
            disabled: '#4B5563',
          },
          syntax: {
            keyword: '#C792EA',
            function: '#82AAFF',
            string: '#C3E88D',
            number: '#F78C6C',
            comment: '#546E7A',
            variable: '#EEFFFF',
            tag: '#F07178',
            attribute: '#C792EA',
          },
        },
      },
      spacing: {
        'sidebar-collapsed': '60px',
        'sidebar': '240px',
        'sidebar-right': '280px',
        'header': '60px',
        'statusbar': '32px',
      },
      maxWidth: {
        'content': '1280px',
        'command-palette': '600px',
      },
      height: {
        'header': '60px',
        'statusbar': '32px',
        'input': '48px',
        'button': '40px',
        'list-item': '32px',
      },
      borderRadius: {
        'sm': '4px',
        DEFAULT: '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Oxygen', 'Ubuntu', 'sans-serif'],
        mono: ['"Fira Code"', '"JetBrains Mono"', 'Monaco', 'Consolas', '"Courier New"', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],      // 12px
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],  // 14px
        'base': ['1rem', { lineHeight: '1.5rem' }],     // 16px
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],  // 18px
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],   // 20px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],      // 24px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
      },
      boxShadow: {
        'sm': '0 1px 2px rgba(0, 0, 0, 0.3)',
        DEFAULT: '0 4px 6px rgba(0, 0, 0, 0.3)',
        'md': '0 4px 6px rgba(0, 0, 0, 0.3)',
        'lg': '0 10px 15px rgba(0, 0, 0, 0.4)',
        'xl': '0 20px 25px rgba(0, 0, 0, 0.5)',
        '2xl': '0 25px 50px rgba(0, 0, 0, 0.6)',
        'focus': '0 0 0 3px rgba(59, 130, 246, 0.1)',
      },
      transitionDuration: {
        'fast': '100ms',
        DEFAULT: '150ms',
        'slow': '300ms',
      },
      transitionTimingFunction: {
        DEFAULT: 'ease-in-out',
      },
      backdropBlur: {
        'xs': '2px',
        'sm': '4px',
        DEFAULT: '12px',
        'lg': '16px',
      },
      zIndex: {
        'base': 0,
        'dropdown': 10,
        'sticky': 20,
        'fixed': 30,
        'modal-backdrop': 40,
        'modal': 50,
        'popover': 60,
        'tooltip': 70,
        'toast': 80,
        'notification': 80,
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease-in-out',
        'fade-out': 'fadeOut 150ms ease-in-out',
        'slide-up': 'slideUp 300ms ease-out',
        'slide-down': 'slideDown 300ms ease-out',
        'scale-in': 'scaleIn 200ms ease-out',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}
