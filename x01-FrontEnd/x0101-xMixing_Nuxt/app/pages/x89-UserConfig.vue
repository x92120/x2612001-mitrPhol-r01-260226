<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'

interface User {
  id?: number
  username: string
  email: string
  full_name: string
  role: string
  department: string
  status: string
  permissions: string[]
  last_login?: string
  password?: string
  new_password?: string
}

const $q = useQuasar()
const { getAuthHeader } = useAuth()
const selectedUser = ref<User | null>(null)
const isCreateDialogOpen = ref(false)
const newUser = ref<User>({
  username: '',
  email: '',
  full_name: '',
  role: 'Operator',
  department: '',
  status: 'Active',
  permissions: [],
  password: ''
})
const searchQuery = ref('')
const isLoading = ref(false)

// Users list
const users = ref<User[]>([])

// Available permissions
const allPermissions = ref([
  { value: 'sku_management', label: 'SKU Management' },
  { value: 'ingredient_receipt', label: 'Ingredient Receipt' },
  { value: 'production_planning', label: 'Production Planning' },
  { value: 'production_list', label: 'Production List' },
  { value: 'prepare_batch', label: 'Prepare Batch' },
  { value: 'admin', label: 'Admin' },
])

// Roles
const roles = ['Admin', 'Manager', 'Operator', 'QC Inspector', 'Viewer']

const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const query = searchQuery.value.toLowerCase()
  return users.value.filter(u => 
    (u.full_name?.toLowerCase().includes(query)) || 
    (u.email?.toLowerCase().includes(query)) ||
    (u.username?.toLowerCase().includes(query)) ||
    (u.role?.toLowerCase().includes(query)) ||
    (u.department?.toLowerCase().includes(query))
  )
})

const selectUser = (user: User) => {
  selectedUser.value = { ...user }
}

const fetchUsers = async () => {
  isLoading.value = true
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/users/`, {
      headers: getAuthHeader() as Record<string, string>,
    })
    if (response.ok) {
      users.value = await response.json()
    } else {
      $q.notify({
        type: 'negative',
        message: 'Failed to fetch users',
        position: 'top',
      })
    }
  } catch (error) {
    console.error('Error fetching users:', error)
    $q.notify({
      type: 'negative',
      message: 'Error fetching users',
      position: 'top',
    })
  } finally {
    isLoading.value = false
  }
}

const saveUserChanges = async () => {
  if (!selectedUser.value) return

  isLoading.value = true
  try {
    const payload: any = {
      username: selectedUser.value.username,
      full_name: selectedUser.value.full_name,
      email: selectedUser.value.email,
      role: selectedUser.value.role,
      department: selectedUser.value.department,
      status: selectedUser.value.status,
      permissions: selectedUser.value.permissions,
    }

    if (selectedUser.value.new_password) {
      payload.password = selectedUser.value.new_password
    }

    const response = await fetch(`${appConfig.apiBaseUrl}/users/${selectedUser.value.id}`, {
      method: 'PUT',
      headers: {
        ...getAuthHeader() as Record<string, string>,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (response.ok) {
      const updatedUser = await response.json()
      const index = users.value.findIndex((u) => u.id === updatedUser.id)
      if (index !== -1) {
        users.value[index] = updatedUser
      }
      $q.notify({
        type: 'primary',
        message: 'User updated successfully!',
        position: 'top',
      })
      selectedUser.value = null
    } else {
      const errorData = await response.json()
      let errorMessage = 'Failed to update user'
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail
      } else if (Array.isArray(errorData.detail)) {
        // Handle Pydantic validation errors
        errorMessage = errorData.detail.map((err: any) => err.msg).join(', ')
      } else if (typeof errorData.detail === 'object') {
        errorMessage = JSON.stringify(errorData.detail)
      }
      throw new Error(errorMessage)
    }
  } catch (error: any) {
    console.error('Error updating user:', error)
    $q.notify({
      type: 'negative',
      message: error.message || 'Failed to update user',
      position: 'top',
    })
  } finally {
    isLoading.value = false
  }
}

const createUser = async () => {
  isLoading.value = true
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/users/`, {
      method: 'POST',
      headers: {
        ...getAuthHeader() as Record<string, string>,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newUser.value),
    })

    if (response.ok) {
      const createdUser = await response.json()
      users.value.push(createdUser)
      $q.notify({
        type: 'primary',
        message: 'User created successfully!',
        position: 'top',
      })
      closeCreateDialog()
    } else {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to create user')
    }
  } catch (error: any) {
    console.error('Error creating user:', error)
    $q.notify({
      type: 'negative',
      message: error.message || 'Failed to create user',
      position: 'top',
    })
  } finally {
    isLoading.value = false
  }
}

const closeCreateDialog = () => {
  isCreateDialogOpen.value = false
  newUser.value = {
    username: '',
    email: '',
    full_name: '',
    role: 'Operator',
    department: '',
    status: 'Active',
    permissions: [],
    password: ''
  }
}


onMounted(() => {
  fetchUsers()
})

const togglePermission = (permission: string) => {
  if (!selectedUser.value) return
  const index = selectedUser.value.permissions.indexOf(permission)
  if (index > -1) {
    selectedUser.value.permissions.splice(index, 1)
  } else {
    selectedUser.value.permissions.push(permission)
  }
}

const hasPermission = (permission: string) => {
  return selectedUser.value && selectedUser.value.permissions.includes(permission)
}

const closeDialog = () => {
  selectedUser.value = null
}

const deleteUser = (user: User) => {
  $q.dialog({
    title: 'Delete User',
    message: `Are you sure you want to delete "${user.full_name || user.username}"? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    color: 'negative',
  }).onOk(async () => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/users/${user.id}`, {
        method: 'DELETE',
        headers: getAuthHeader() as Record<string, string>,
      })
      if (response.ok) {
        users.value = users.value.filter(u => u.id !== user.id)
        $q.notify({ type: 'positive', message: `User "${user.full_name || user.username}" deleted`, position: 'top' })
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete user')
      }
    } catch (error: any) {
      $q.notify({ type: 'negative', message: error.message || 'Failed to delete user', position: 'top' })
    }
  })
}
</script>

<template>
  <q-page class="q-pa-md" style="background-color: #f5f5f5">
    <!-- Header -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="shadow-1">
          <q-card-section class="bg-info text-white">
            <div class="text-h6 text-weight-bold">User Access Management</div>
          </q-card-section>

          <q-form class="q-pa-md">
            <!-- Search Section -->
            <div class="row q-col-gutter-md q-mb-md">
              <div class="col-12 row items-center no-wrap">
                <q-input
                  v-model="searchQuery"
                  outlined
                  label="Search users by name or email..."
                  dense
                  class="col"
                >
                  <template v-slot:prepend>
                    <q-icon name="search" color="info" />
                  </template>
                </q-input>
                <q-btn
                  label="Add User"
                  color="primary"
                  icon="add"
                  class="q-ml-md"
                  @click="isCreateDialogOpen = true"
                />
              </div>
            </div>
          </q-form>
        </q-card>
      </div>
    </div>

    <!-- Users Table -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="shadow-1">
          <q-table
            :rows="filteredUsers"
            :columns="[
              { name: 'full_name', label: 'Name', field: 'full_name', align: 'left' },
              { name: 'email', label: 'Email', field: 'email', align: 'left' },
              { name: 'role', label: 'Role', field: 'role', align: 'left' },
              { name: 'department', label: 'Department', field: 'department', align: 'left' },
              { name: 'status', label: 'Status', field: 'status', align: 'center' },
              { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
            ]"
            row-key="id"
            flat
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-chip
                  :label="props.row.status"
                  :color="props.row.status === 'Active' ? 'primary' : 'negative'"
                  text-color="white"
                  size="sm"
                />
              </q-td>
            </template>

            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  label="Manage"
                  color="info"
                  size="sm"
                  padding="xs md"
                  class="text-white text-weight-bold q-mr-sm"
                  @click="selectUser(props.row)"
                />
                <q-btn
                  label="Delete"
                  color="negative"
                  size="sm"
                  padding="xs md"
                  class="text-white text-weight-bold"
                  icon="delete"
                  @click="deleteUser(props.row)"
                />
              </q-td>
            </template>
          </q-table>
        </q-card>
      </div>
    </div>

    <!-- Create User Dialog -->
    <q-dialog v-model="isCreateDialogOpen" persistent>
      <q-card style="min-width: 400px">
        <q-card-section class="bg-primary text-white">
          <div class="row items-center">
            <div class="text-h6">Add New User</div>
            <q-space />
            <q-btn icon="close" flat round dense @click="closeCreateDialog" />
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none q-pa-lg">
          <q-form @submit.prevent="createUser" class="q-gutter-md">
             <q-input
              filled
              v-model="newUser.username"
              label="Username *"
              hint="Unique identifier"
              lazy-rules
              :rules="[ val => val && val.length > 0 || 'Please type something']"
            />
             <q-input
              filled
              v-model="newUser.email"
              label="Email *"
              type="email"
              lazy-rules
              :rules="[ val => val && val.length > 0 || 'Please type something']"
            />
            <q-input
              filled
              v-model="newUser.password"
              label="Password *"
              type="password"
              lazy-rules
              :rules="[ val => val && val.length >= 6 || 'Password must be at least 6 characters']"
            />
            <q-input
              filled
              v-model="newUser.full_name"
              label="Full Name"
            />
             <q-select
              filled
              v-model="newUser.role"
              :options="roles"
              label="Role"
            />
             <q-input
              filled
              v-model="newUser.department"
              label="Department"
            />

            <div align="right">
              <q-btn label="Cancel" flat color="primary" v-close-popup class="q-mr-sm" @click="closeCreateDialog" />
              <q-btn label="Create User" type="submit" color="primary" :loading="isLoading" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- User Permissions Dialog -->
    <q-dialog
      :model-value="selectedUser !== null"
      position="right"
      :maximized="false"
      @update:model-value="
        (val) => {
          if (!val) closeDialog()
        }
      "
      @hide="closeDialog"
    >
      <q-card style="min-width: 800px; max-width: 900px" v-if="selectedUser">
        <!-- Dialog Header -->
        <q-card-section class="bg-info text-white">
          <div class="row items-center">
            <div class="col">
              <div class="text-h6 text-weight-bold">{{ selectedUser.full_name }}</div>
              <div style="font-size: 0.9rem">{{ selectedUser.email }}</div>
            </div>
            <q-btn icon="close" flat round dense @click="closeDialog" />
          </div>
        </q-card-section>

        <q-card-section class="q-pa-lg">
          <div class="row q-col-gutter-xl">
            <!-- Left Column: User Info -->
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-weight-bold q-mb-md">User Information</div>
              
              <div class="q-mb-md">
                <div class="text-caption">Username</div>
                <q-input v-model="selectedUser.username" outlined dense />
              </div>

              <div class="q-mb-md">
                <div class="text-caption">Full Name</div>
                <q-input v-model="selectedUser.full_name" outlined dense />
              </div>

              <div class="q-mb-md">
                <div class="text-caption">Email</div>
                <q-input v-model="selectedUser.email" outlined dense />
              </div>

              <div class="q-mb-md">
                <div class="text-caption">Role</div>
                <q-select v-model="selectedUser.role" outlined :options="roles" dense emit-value />
              </div>

              <div class="q-mb-md">
                <div class="text-caption">Department</div>
                <q-input v-model="selectedUser.department" outlined dense />
              </div>

              <div class="q-mb-md">
                <div class="text-caption">Status</div>
                <q-select
                  v-model="selectedUser.status"
                  outlined
                  :options="['Active', 'Inactive']"
                  dense
                  emit-value
                />
              </div>
              
              <div class="q-mt-lg">
                <q-expansion-item
                  icon="lock"
                  label="Change Password"
                  header-class="bg-grey-2 text-grey-8"
                  expand-icon-class="text-grey-8"
                  default-closed
                >
                  <q-card>
                    <q-card-section class="q-pa-sm">
                      <q-input 
                        v-model="selectedUser.new_password" 
                        outlined 
                        dense 
                        label="New Password" 
                        type="password"
                        hint="Leave empty to keep current password"
                      />
                    </q-card-section>
                  </q-card>
                </q-expansion-item>
              </div>
            </div>

            <!-- Right Column: Permissions -->
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 text-weight-bold q-mb-md">Permissions</div>
              <q-separator class="q-mb-md" />

              <div class="column q-gutter-sm">
                <q-checkbox
                  v-for="permission in allPermissions"
                  :key="permission.value"
                  :model-value="hasPermission(permission.value)"
                  :label="permission.label"
                  color="info"
                  @update:model-value="togglePermission(permission.value)"
                />
              </div>
            </div>
          </div>
        </q-card-section>

        <!-- Dialog Actions -->
        <q-card-section class="text-right bg-info text-white">
          <q-btn
            label="Cancel"
            flat
            class="q-mr-sm text-white text-weight-bold"
            @click="closeDialog"
          />
          <q-btn
            label="Save Changes"
            color="white"
            text-color="info"
            class="text-weight-bold"
            :loading="isLoading"
            @click="saveUserChanges"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
:deep(.q-table__card) {
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.1);
}
</style>
