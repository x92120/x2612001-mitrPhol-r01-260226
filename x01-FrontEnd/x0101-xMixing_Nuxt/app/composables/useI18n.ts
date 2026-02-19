/**
 * useI18n Composable
 * ==================
 * Provides reactive language switching between English and Thai.
 * 
 * Data source priority:
 *   1. SQLite database via API (fetched on init)
 *   2. Built-in static dictionary (offline fallback)
 * 
 * Usage:
 *   const { t, locale, toggleLocale, setLocale } = useI18n()
 *   
 *   // In template:
 *   {{ t('nav.home') }}        → "Home" or "หน้าหลัก"
 *   {{ t('common.save') }}     → "Save" or "บันทึก"
 */

import { dictionary, type Locale } from '~/i18n/dictionary'
import { appConfig } from '~/appConfig/config'

// Shared reactive state across all components
const locale = ref<Locale>((process.client ? localStorage.getItem('app_locale') : null) as Locale || 'en')

// Live dictionary loaded from API (overrides static dictionary)
const liveDictionary = ref<Record<string, Record<string, string>>>({})
const isLoaded = ref(false)

/**
 * Fetch translations from SQLite backend
 * Merges with static dictionary (API values take priority)
 */
const fetchTranslations = async () => {
    if (!process.client) return

    try {
        const response = await fetch(`${appConfig.apiBaseUrl}/translations/`)
        if (response.ok) {
            const data = await response.json()
            liveDictionary.value = data
            isLoaded.value = true
            console.log('✅ i18n: Loaded translations from database')
        }
    } catch (error) {
        console.warn('⚠️ i18n: Could not fetch from API, using built-in dictionary', error)
    }
}

// Fetch on first load (client-side only)
if (process.client && !isLoaded.value) {
    fetchTranslations()
}

export const useI18n = () => {

    /**
     * Translate a key to the current locale
     * Priority: API dictionary → static dictionary → key itself
     */
    const t = (key: string, params?: Record<string, string | number>): string => {
        // Try live dictionary first (from SQLite), then fall back to static
        let text =
            liveDictionary.value[locale.value]?.[key] ||
            dictionary[locale.value]?.[key] ||
            liveDictionary.value['en']?.[key] ||
            dictionary['en']?.[key] ||
            key

        // Simple parameter interpolation: {name} → value
        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
            })
        }

        return text
    }

    /**
     * Toggle between English and Thai
     */
    const toggleLocale = () => {
        locale.value = locale.value === 'en' ? 'th' : 'en'
        if (process.client) {
            localStorage.setItem('app_locale', locale.value)
        }
    }

    /**
     * Set a specific locale
     */
    const setLocale = (newLocale: Locale) => {
        locale.value = newLocale
        if (process.client) {
            localStorage.setItem('app_locale', locale.value)
        }
    }

    /**
     * Reload translations from API
     */
    const reloadTranslations = () => fetchTranslations()

    /**
     * Get current locale display name
     */
    const localeName = computed(() => locale.value === 'en' ? 'English' : 'ไทย')

    /**
     * Get the flag/icon for the current locale
     */
    const localeFlag = computed(() => locale.value === 'en' ? '🇬🇧' : '🇹🇭')

    /**
     * Check if current locale is Thai
     */
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
