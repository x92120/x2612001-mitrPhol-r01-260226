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
          <q-avatar>
            <img src="/logo.svg" />
          </q-avatar>
          xBatch
        </q-toolbar-title>

        <q-btn to="/x80-UserLogin" label="Login" flat icon="login" v-if="!user" />
        <q-btn label="Logout" flat icon="logout" v-if="user" @click="handleLogout" />
      </q-toolbar>

      <q-tabs align="left">
        <q-route-tab to="/" label="Home" />
        <q-route-tab
          to="/x10-IngredientIntake"
          label="Ingredient Intake"
          v-if="hasPermission('ingredient_receipt')"
        />
        <q-route-tab to="/x20-Sku" label="SKU" v-if="hasPermission('sku_management')" />
        <q-route-tab
          to="/x30-ProductionPlan"
          label="Production Plan"
          v-if="hasPermission('production_planning')"
        />
        <q-route-tab
          to="/x40-PreBatch"
          label="Batch Prepare"
          v-if="hasPermission('prepare_batch')"
        />
        <q-route-tab
          to="/x50-PackingList"
          label="Packing List"
          v-if="hasPermission('production_list')"
        />
        <q-route-tab
          to="/x60-BatchRecheck"
          label="BATCH RE CHECK"
          v-if="hasPermission('production_list')"
        />
        <q-route-tab to="/x89-UserConfig" label="User" v-if="hasPermission('admin')" />
        <q-route-tab to="/x90-ServerStatus" label="Server Status" v-if="hasPermission('admin')" />
        <q-route-tab to="/x99-About" label="About" />
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
