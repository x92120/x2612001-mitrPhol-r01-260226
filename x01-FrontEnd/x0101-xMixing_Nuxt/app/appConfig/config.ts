/**
 * Application Configuration and Utilities
 * Refactored for Nuxt 4 & TypeScript
 */

export const appConfig = {
  // Base URL for API calls - always port 8001 on the same host the browser is using
  get apiBaseUrl(): string {
    if (typeof window === 'undefined') return 'http://localhost:8001'
    // Use the exact hostname the browser used to load this page.
    // This ensures it works both on localhost and over network (IP or hostname).
    const { protocol, hostname } = window.location
    return `${protocol}//${hostname}:8001`
  }
}


