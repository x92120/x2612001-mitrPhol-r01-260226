/**
 * useI18n Composable
 * ==================
 * Provides reactive language switching between English and Thai.
 * 
 * Usage:
 *   const { t, locale, toggleLocale, setLocale } = useI18n()
 *   
 *   // In template:
 *   {{ t('nav.home') }}        → "Home" or "หน้าหลัก"
 *   {{ t('common.save') }}     → "Save" or "บันทึก"
 */

import { dictionary, type Locale } from '~/i18n/dictionary'

// Shared reactive state across all components
const locale = ref<Locale>((process.client ? localStorage.getItem('app_locale') : null) as Locale || 'en')

export const useI18n = () => {

    /**
     * Translate a key to the current locale
     * Falls back to English if key not found in current locale
     * Falls back to the key itself if not found in any locale
     */
    const t = (key: string, params?: Record<string, string | number>): string => {
        let text = dictionary[locale.value]?.[key] || dictionary['en']?.[key] || key

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
        localeName,
        localeFlag,
        isThai,
    }
}
