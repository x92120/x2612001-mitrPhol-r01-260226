import { fileURLToPath } from 'node:url'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      title: 'xMixing 2025',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'xMixing Control System 2025 - Production Management' },
        { name: 'application-name', content: 'xMixing 2025' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/images/logo-icon.svg' }
      ]
    }
  },
  modules: [
    'nuxt-quasar-ui'
  ],
  quasar: {
    sassVariables: fileURLToPath(new URL('./app/assets/quasar-variables.sass', import.meta.url)),
    plugins: [
      'Notify',
      'Dialog'
    ],
    extras: {
      fontIcons: ['material-icons']
    }
  },
  devtools: { enabled: true },
  future: {
    compatibilityVersion: 4,
  },
  compatibilityDate: '2024-11-01',
})
