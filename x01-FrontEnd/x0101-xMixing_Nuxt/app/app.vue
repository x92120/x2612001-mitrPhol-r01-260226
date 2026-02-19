<script setup lang="ts">
const { hasPermission, user, logout } = useAuth()
const $q = useQuasar()

const handleLogout = async () => {
  await logout()
  $q.notify({
    type: 'info',
    message: 'Logged out successfully',
    position: 'top',
  })
  navigateTo('/')
}
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white" height-hint="98">
      <q-toolbar>
        <q-toolbar-title>
          <div class="row items-center q-gutter-sm">
            <svg width="120" height="36" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg" style="display: block;">
              <!-- Rounded Rectangle: Yellow Fill (#FFB800), Red Border (#8B1A1A) -->
              <rect x="5" y="5" width="190" height="50" rx="10" ry="10" 
                    fill="#FFB800" 
                    stroke="#8B1A1A" 
                    stroke-width="4" />
              <!-- "xMixing" Text: Courier New, Bold, Red (#8B1A1A) -->
              <text x="100" y="38" 
                    font-family="'Courier New', Courier, monospace" 
                    font-size="34" 
                    font-weight="bold" 
                    fill="#8B1A1A" 
                    text-anchor="middle" 
                    letter-spacing="1">xMixing</text>
              <!-- Underline: Red (#8B1A1A) -->
              <line x1="40" y1="46" x2="160" y2="46" 
                    stroke="#8B1A1A" 
                    stroke-width="3" 
                    stroke-linecap="round" />
            </svg>
          </div>
        </q-toolbar-title>

        <q-btn to="/x80-UserLogin" label="Login" flat icon="login" v-if="!user" />
        <q-btn label="Logout" flat icon="logout" v-if="user" @click="handleLogout" />
      </q-toolbar>

      <q-tabs align="left" dense>
        <q-route-tab to="/" icon="home" label="Home" />
        <q-route-tab
          to="/x10-IngredientIntake"
          icon="local_shipping"
          label="Ingredient Intake"
          v-if="hasPermission('ingredient_receipt')"
        />
        <q-route-tab to="/x20-Sku" icon="inventory_2" label="SKU" v-if="hasPermission('sku_management')" />
        <q-route-tab
          to="/x30-ProductionPlan"
          icon="account_tree"
          label="Production Plan"
          v-if="hasPermission('production_planning')"
        />
        <q-route-tab
          to="/x40-PreBatch"
          icon="science"
          label="Batch Prepare"
          v-if="hasPermission('prepare_batch')"
        />
        <q-route-tab
          to="/x50-PackingList"
          icon="view_list"
          label="Packing List"
          v-if="hasPermission('production_list')"
        />
        <q-route-tab
          to="/x60-BatchRecheck"
          icon="fact_check"
          label="Batch Re-Check"
          v-if="hasPermission('production_list')"
        />
        <q-route-tab to="/x89-UserConfig" icon="manage_accounts" label="User" v-if="hasPermission('admin')" />
        <q-route-tab to="/x90-systemDashboard" icon="dashboard" label="System Dashboard" v-if="hasPermission('admin')" />
        <q-route-tab to="/x99-About" icon="info" label="About" />
      </q-tabs>
    </q-header>

    <q-page-container>
      <NuxtPage />
    </q-page-container>
  </q-layout>
</template>

<style>
/* Global styles if needed */
</style>
