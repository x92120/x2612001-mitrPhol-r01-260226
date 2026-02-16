export default defineNuxtRouteMiddleware((to, from) => {
    const { user, hasPermission } = useAuth()

    // Public pages (exact matches or starts with)
    const publicPages = ['/x80-UserLogin', '/x81-UserRegister', '/', '/x99-About']

    if (publicPages.includes(to.path)) {
        return
    }

    // Check if user is logged in
    if (!user.value) {
        return navigateTo({
            path: '/x80-UserLogin',
            query: { redirect: to.fullPath }
        })
    }

    // Check for specific permissions based on the path
    const permissionMap: Record<string, string> = {
        '/x89-UserConfig': 'admin',
        '/x10-IngredientIntake': 'ingredient_receipt',
        '/x11-IngredientConfig': 'ingredient_receipt',
        '/x12-WarehouseConfig': 'ingredient_receipt',
        '/x13-IngredientIntakeReport': 'ingredient_receipt',
        '/x20-Sku': 'sku_management',
        '/x30-ProductionPlan': 'production_planning',
        '/x30-ProductionPlan/plant-config': 'production_planning',
        '/x40-PreBatch': 'prepare_batch',
        '/x50-PackingList': 'production_list',
        '/x60-BatchRecheck': 'production_list',
        '/x90-ServerStatus': 'admin',
    }

    const requiredPermission = permissionMap[to.path]
    if (requiredPermission && !hasPermission(requiredPermission)) {
        return navigateTo({
            path: '/',
            query: { error: 'no-permission' }
        })
    }
})
