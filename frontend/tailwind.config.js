/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
        colors: {
                background: "hsl(var(--background) / <alpha-value>)",
                foreground: "hsl(var(--foreground) / <alpha-value>)",
                card: "hsl(var(--card) / <alpha-value>)",
                "card-foreground": "hsl(var(--card-foreground) / <alpha-value>)",
                popover: "hsl(var(--popover) / <alpha-value>)",
                "popover-foreground": "hsl(var(--popover-foreground) / <alpha-value>)",
                primary: "hsl(var(--primary) / <alpha-value>)",
                "primary-foreground": "hsl(var(--primary-foreground) / <alpha-value>)",
                secondary: "hsl(var(--secondary) / <alpha-value>)",
                "secondary-foreground": "hsl(var(--secondary-foreground) / <alpha-value>)",
                muted: "hsl(var(--muted) / <alpha-value>)",
                "muted-foreground": "hsl(var(--muted-foreground) / <alpha-value>)",
                accent: "hsl(var(--accent) / <alpha-value>)",
                "accent-foreground": "hsl(var(--accent-foreground) / <alpha-value>)",
                destructive: "hsl(var(--destructive) / <alpha-value>)",
                "destructive-foreground": "hsl(var(--destructive-foreground) / <alpha-value>)",
                border: "hsl(var(--border) / <alpha-value>)",
                input: "hsl(var(--input) / <alpha-value>)",
                ring: "hsl(var(--ring) / <alpha-value>)",
                // Liquid Glass Blob Colors
                "blob-1": "hsl(var(--blob-color-1) / <alpha-value>)",
                "blob-2": "hsl(var(--blob-color-2) / <alpha-value>)",
                "blob-3": "hsl(var(--blob-color-3) / <alpha-value>)",
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            fontFamily: {
                sans: ['Outfit', 'sans-serif'],
            },
            keyframes: {
                blob: {
                    "0%": { transform: "translate(0px, 0px) scale(1)" },
                    "33%": { transform: "translate(30px, -50px) scale(1.2)" },
                    "66%": { transform: "translate(-20px, 20px) scale(0.8)" },
                    "100%": { transform: "translate(0px, 0px) scale(1)" },
                },
                float: {
                    "0%, 100%": { transform: "translateY(0)" },
                    "50%": { transform: "translateY(-20px)" },
                },
            },
            animation: {
                blob: "blob 10s infinite",
                float: "float 6s ease-in-out infinite",
            },
        },
    },
    plugins: [],
}
