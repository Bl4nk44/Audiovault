import { useStore } from '../store/useStore'
import { translations } from '../i18n/translations'

export function useTranslation() {
    const user = useStore(state => state.user)
    const language = (user?.preferences?.language as keyof typeof translations) || 'en'

    // Simple recursive lookup
    const t = (path: string): string => {
        const keys = path.split('.')
        let current: any = translations[language] || translations['en']

        for (const key of keys) {
            if (current === undefined || current[key] === undefined) {
                // Fallback to English if translation missing
                if (language !== 'en') {
                    let fallback: any = translations['en']
                    for (const fKey of keys) {
                        if (fallback === undefined || fallback[fKey] === undefined) return path
                        fallback = fallback[fKey]
                    }
                    return fallback as string
                }
                return path
            }
            current = current[key]
        }
        return current as string
    }

    return { t, language }
}
