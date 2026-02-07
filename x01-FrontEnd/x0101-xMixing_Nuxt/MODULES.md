# xMixing Frontend - Module Installation Guide

## 📦 Installed Modules

### Core Framework
- **Nuxt 4.3.0** - Vue.js meta-framework for production-ready applications
- **Vue 3.5.27** - Progressive JavaScript framework
- **Vue Router 4.6.4** - Official router for Vue.js

### UI Framework
- **Quasar 2.18.6** - High-performance Material Design component framework
- **@quasar/extras 1.17.0** - Icon sets, fonts, and animations for Quasar
- **nuxt-quasar-ui 3.0.0** - Nuxt module for Quasar integration

### Data Visualization
- **ApexCharts 5.3.6** - Modern charting library
- **vue3-apexcharts 1.10.0** - Vue 3 wrapper for ApexCharts

### Real-time Communication
- **MQTT 5.14.1** - MQTT protocol client for IoT device communication (scales, sensors)

### Development Tools
- **@playwright/test 1.58.1** - End-to-end testing framework
- **sass-embedded 1.97.3** - Sass/SCSS preprocessor for styling
- **TypeScript** - Type-safe JavaScript (via Nuxt)

## 🚀 Installation Commands

### Fresh Installation
```bash
cd x01-FrontEnd/x0101-xMixing_Nuxt
npm install
```

### Install Specific Modules
```bash
# Core dependencies
npm install nuxt@^4.3.0 vue@^3.5.27 vue-router@^4.6.4

# UI Framework
npm install quasar@^2.18.6 @quasar/extras@^1.17.0 nuxt-quasar-ui@^3.0.0

# Charts
npm install apexcharts@^5.3.6 vue3-apexcharts@^1.10.0

# MQTT for real-time scale data
npm install mqtt@^5.14.1

# Dev dependencies
npm install -D @playwright/test@^1.58.1 sass-embedded@^1.97.3
```

## 📋 Module Usage in Application

### Quasar Components
Used throughout the application for UI components:
- **Tables**: `q-table` for ingredient lists, production plans
- **Forms**: `q-input`, `q-select`, `q-btn` for data entry
- **Dialogs**: `q-dialog` for modals and confirmations
- **Notifications**: `q-notify` for user feedback
- **Cards**: `q-card` for content containers
- **Layout**: `q-page`, `q-layout` for page structure

### ApexCharts
Used for data visualization:
- Production volume charts
- Ingredient usage trends
- Real-time monitoring dashboards

### MQTT
Used for real-time device communication:
- Scale weight readings (x40-PreBatch.vue)
- Sensor data from production equipment
- Live updates from mixing stations

### Quasar Plugins Enabled
```typescript
quasar: {
  plugins: [
    'Notify',  // Toast notifications
    'Dialog'   // Modal dialogs
  ],
  extras: {
    fontIcons: ['material-icons']  // Material Design icons
  }
}
```

## 🔧 Configuration Files

### package.json
Main dependency configuration file

### nuxt.config.ts
Nuxt and Quasar configuration:
- Module registration
- Quasar plugin setup
- Sass variables
- Development tools

### tsconfig.json
TypeScript configuration for type checking

### playwright.config.ts
E2E testing configuration

## 📱 Key Features Enabled

1. **Material Design UI** - Professional, responsive interface via Quasar
2. **Real-time Updates** - MQTT for live scale readings and sensor data
3. **Data Visualization** - Charts for production analytics
4. **Type Safety** - TypeScript for robust code
5. **E2E Testing** - Playwright for automated testing
6. **Responsive Design** - Mobile-first approach with Quasar
7. **Component Library** - Rich set of pre-built UI components

## 🎨 Styling

- **Sass/SCSS** support via sass-embedded
- **Quasar Variables** customization in `app/assets/quasar-variables.sass`
- **Material Icons** font included

## 🧪 Testing

```bash
# Run E2E tests
npx playwright test

# Run specific test
npx playwright test screenshot-capture.spec.ts
```

## 🏃 Running the Application

```bash
# Development mode
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Generate static site
npm run generate
```

## 📊 Application Structure

```
x01-FrontEnd/x0101-xMixing_Nuxt/
├── app/
│   ├── pages/           # Route pages
│   ├── components/      # Reusable components
│   ├── composables/     # Vue composables (useAuth, useMQTT)
│   ├── appConfig/       # App configuration
│   └── assets/          # Styles and static assets
├── public/              # Static files
├── node_modules/        # Installed packages
├── package.json         # Dependencies
└── nuxt.config.ts       # Nuxt configuration
```

## 🔄 Update Modules

```bash
# Check for updates
npm outdated

# Update all to latest compatible versions
npm update

# Update specific package
npm install quasar@latest
```

## 💡 Notes

- All modules are already installed and configured
- The application is currently running on `http://0.0.0.0:3000`
- MQTT is configured for scale communication
- Quasar provides a complete Material Design component library
- ApexCharts handles all data visualization needs
