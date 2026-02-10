/**
 * Application Configuration and Utilities
 * Refactored for Nuxt 4 & TypeScript
 */

export const appConfig = {
  // Base URL for API calls - defaults to port 8001 on the same host
  get apiBaseUrl(): string {
    const hostname = (typeof window !== 'undefined' && window.location) ? window.location.hostname : 'localhost'
    return `http://${hostname}:8000`
  }
}


