import type { StorybookConfig } from '@storybook/vue3-vite';
import vue from '@vitejs/plugin-vue';

const config: StorybookConfig = {
  stories: [
    "../stories/**/*.mdx",
    "../stories/**/*.stories.@(js|jsx|mjs|ts|tsx)",
    "../app/components/**/*.stories.@(js|jsx|mjs|ts|tsx)"
  ],
  addons: [
    "@chromatic-com/storybook",
    "@storybook/addon-vitest",
    "@storybook/addon-a11y",
    "@storybook/addon-docs",
    "@storybook/addon-onboarding"
  ],
  framework: "@storybook/vue3-vite",
  async viteFinal(config) {
    // Ensure Vue plugin is configured
    config.plugins = config.plugins || [];
    if (!config.plugins.some((plugin: any) => plugin?.name === 'vite:vue')) {
      config.plugins.push(vue());
    }

    // Add Quasar support
    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...config.resolve.alias,
      'quasar': 'quasar/dist/quasar.esm.js'
    };

    return config;
  }
};
export default config;