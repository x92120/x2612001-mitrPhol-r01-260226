import { ref, computed } from 'vue'

export interface User {
    id: number
    username: string
    email: string
    full_name: string
    role: string
    department: string
    status: string
    permissions: string[]
}

// Global state using Nuxt useCookie for SSR-safe persistence
// This allows the auth state to be available during the first server render
const user = ref<User | null>(null)
const token = ref<string | null>(null)

export function useAuth() {
    const cookieUser = useCookie<User | null>('user')
    const cookieToken = useCookie<string | null>('token')

    // Sync state with cookies on the first call
    if (!user.value && cookieUser.value) {
        user.value = cookieUser.value
    }
    if (!token.value && cookieToken.value) {
        token.value = cookieToken.value
    }

    const isAuthenticated = computed(() => !!token.value)

    /**
     * Check if user has specific permission
     */
    const hasPermission = (permission: string): boolean => {
        if (!user.value) return false
        // Admins bypass all permission checks
        if (user.value.role === 'Admin') return true
        return user.value.permissions?.includes(permission) || false
    }

    /**
     * Check if user has any of the provided permissions
     */
    const hasAnyPermission = (permissions: string[]): boolean => {
        if (!user.value) return false
        if (user.value.role === 'Admin') return true
        return permissions.some(p => hasPermission(p))
    }

    /**
     * Update auth state after login
     */
    const login = (userData: User, authToken: string) => {
        user.value = userData
        token.value = authToken
        cookieUser.value = userData
        cookieToken.value = authToken
    }

    /**
     * Clear auth state
     */
    const logout = () => {
        user.value = null
        token.value = null
        cookieUser.value = null
        cookieToken.value = null
    }

    /**
     * Helper for fetch headers
     */
    const getAuthHeader = () => {
        return token.value ? { Authorization: `Bearer ${token.value}` } : {}
    }

    return {
        user: computed(() => user.value),
        token: computed(() => token.value),
        isAuthenticated,
        hasPermission,
        hasAnyPermission,
        login,
        logout,
        getAuthHeader,
    }
}
