export type Locale = 'en' | 'th'
import { ref, computed } from 'vue'
import { appConfig } from '~/appConfig/config'

/**
 * useI18n Composable
 */
export const useI18n = () => {
    // Shared state using Nuxt useCookie for SSR-safe persistence
    const locale = useCookie<Locale>('app_locale', { default: () => 'en', watch: true })

    // Dictionary state - using useState to share across components and sync SSR/Client
    const liveDictionary = useState<Record<string, Record<string, string>>>('i18n_dictionary', () => ({}))
    const isLoaded = useState('i18n_loaded', () => false)

    /**
     * Fetch translations from API
     */
    const fetchTranslations = async () => {
        try {
            const data = await $fetch<Record<string, Record<string, string>>>(`${appConfig.apiBaseUrl}/translations/`)
            if (data) {
                liveDictionary.value = data
                isLoaded.value = true
                console.log('✅ i18n: Loaded translations')
            }
        } catch (error) {
            console.warn('⚠️ i18n: Fetch failed', error)
        }
    }

    // Initial fetch is now handled by plugins/i18n.init.ts for better SSR support

    /**
     * Translate a key
     */
    const t = (key: string, params?: Record<string, string | number>): string => {
        let text =
            liveDictionary.value[locale.value]?.[key] ||
            liveDictionary.value['en']?.[key] ||
            key

        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
            })
        }
        return text
    }

    const toggleLocale = () => {
        locale.value = locale.value === 'en' ? 'th' : 'en'
    }

    const setLocale = (newLocale: Locale) => {
        locale.value = newLocale
    }

    const reloadTranslations = () => fetchTranslations()
    const localeName = computed(() => locale.value === 'en' ? 'English' : 'ไทย')
    const localeFlag = computed(() => locale.value === 'en' ? '🇬🇧' : '🇹🇭')
    const isThai = computed(() => locale.value === 'th')

    return {
        t,
        locale,
        toggleLocale,
        setLocale,
        reloadTranslations,
        localeName,
        localeFlag,
        isThai,
        isLoaded,
    }
}
