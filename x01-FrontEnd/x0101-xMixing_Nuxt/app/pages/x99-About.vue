<script setup lang="ts">
import { ref } from 'vue'

const applicationVersion = '1.0.0'
const releaseDate = 'January 2026'
const developerName = 'devTeam@xDev.co.th'

const features = ref([
  {
    icon: 'inventory',
    title: 'Ingredient Management',
    description: 'Track and manage ingredient receiving with detailed inventory management.',
  },
  {
    icon: 'menu_book',
    title: 'SKU Management',
    description: 'Create, store, and manage recipes with precise ingredient measurements.',
  },
  {
    icon: 'shopping_cart',
    title: 'Pre-Batch Planning',
    description: 'Plan and prepare batches before production with accurate calculations.',
  },
  {
    icon: 'show_chart',
    title: 'Production Planning',
    description: 'Schedule and organize production runs with timeline management.',
  },
])

const technologies = ref([
  { name: 'Nuxt 4', version: '4.3.0' },
  { name: 'Vue 3', version: '3.5.27' },
  { name: 'Quasar Framework', version: '2.18.6' },
  { name: 'Vite', version: 'Nuxt Built-in' },
  { name: 'Vue Router', version: '4.6.4' },
  { name: 'TypeScript', version: 'Latest' },
])
</script>

<template>
  <q-page class="q-pa-md bg-light-blue-1">
    <!-- Header Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="bg-gradient text-white shadow-4">
          <q-card-section class="text-center q-py-xl">
            <div class="text-h3 q-mb-md text-weight-bold">xMixing</div>
            <div class="text-subtitle1 q-mb-sm">Batch Management & Mixing Control System</div>
            <div class="text-caption">
              Version {{ applicationVersion }} | Released {{ releaseDate }}
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- About Description -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card>
          <q-card-section>
            <div class="text-h5 q-mb-md text-weight-bold">About This Application</div>
            <p class="text-body1 q-mb-md">
              xMixing is a comprehensive batch management and mixing control system designed
              for manufacturing and production environments. This application streamlines the entire
              production workflow from ingredient receiving through final batch production.
            </p>
            <p class="text-body1 q-mb-md">
              Whether you're managing multiple recipes, tracking ingredients, or planning production
              schedules, xMixing provides the tools you need to maintain accuracy,
              efficiency, and quality control throughout your operations.
            </p>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Key Features Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <div class="text-h5 q-mb-md text-weight-bold">Key Features</div>
      </div>
      <div
        v-for="feature in features"
        :key="feature.title"
        class="col-12 col-sm-6 col-md-6 col-lg-3 q-mb-md"
      >
        <q-card class="full-height hover-card">
          <q-card-section class="text-center">
            <q-icon :name="feature.icon" size="3rem" color="light-blue-7" class="q-mb-md" />
            <div class="text-h6 text-weight-bold q-mb-sm">{{ feature.title }}</div>
            <p class="text-caption text-grey-7">{{ feature.description }}</p>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Technology Stack Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card>
          <q-card-section>
            <div class="text-h5 q-mb-md text-weight-bold">Technology Stack</div>
            <div class="row q-col-gutter-md">
              <div v-for="tech in technologies" :key="tech.name" class="col-12 col-sm-6 col-md-4">
                <q-item class="bg-light-blue-7 text-white rounded-borders">
                  <q-item-section avatar>
                    <q-icon name="code" size="lg" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-bold">{{ tech.name }}</q-item-label>
                    <q-item-label caption class="text-grey-3">v{{ tech.version }}</q-item-label>
                  </q-item-section>
                </q-item>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Developer & Copyright Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="bg-light-blue-7 text-white">
          <q-card-section class="text-center">
            <div class="text-h6 q-mb-md">Developed By</div>
            <div class="text-body2 q-mb-lg">{{ developerName }}</div>
            <div class="text-body2 q-mb-md">© 2026 xMixing. All rights reserved.</div>
            <div class="text-caption">Built with Nuxt 4, Vue 3 & Quasar Framework</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Support & Contact Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card>
          <q-card-section>
            <div class="text-h5 q-mb-md text-weight-bold">Support & Feedback</div>
            <p class="text-body2 q-mb-md">
              For support, feature requests, or bug reports, please contact the development team.
            </p>
            <div class="row q-gutter-md">
              <q-btn
                color="light-blue-7"
                label="Contact Support"
                icon="email"
                flat
                @click="$q.notify({ message: 'Support contact information coming soon!' })"
              />
              <q-btn
                color="light-blue-7"
                label="Report Issue"
                icon="bug_report"
                flat
                @click="$q.notify({ message: 'Bug reporting system coming soon!' })"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);
}

.hover-card {
  transition: all 0.3s ease;
}

.hover-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}
</style>
