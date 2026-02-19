# Storybook Installation Guide for xMixing Nuxt App

## ✅ Installation Complete!

Storybook v10.2.7 has been successfully installed for your Nuxt Vue3 application.

## 🚀 Running Storybook

```bash
cd x01-FrontEnd/x0101-xMixing_Nuxt
npm run storybook
```

**Storybook is now running at:**
- Local: http://localhost:6006/
- Network: http://192.168.1.41:6006/

## 📦 Installed Packages

### Core Storybook
- **storybook@^10.2.7** - Main Storybook package
- **@storybook/vue3-vite@^10.2.7** - Vue 3 + Vite integration

### Addons
- **@chromatic-com/storybook@^5.0.0** - Visual testing and review
- **@storybook/addon-vitest@^10.2.7** - Vitest integration for component testing
- **@storybook/addon-a11y@^10.2.7** - Accessibility testing
- **@storybook/addon-docs@^10.2.7** - Auto-generated documentation
- **@storybook/addon-onboarding@^10.2.7** - Interactive onboarding

### Testing Tools
- **vitest** - Unit testing framework
- **playwright** - E2E testing (browser automation)
- **@vitest/browser-playwright** - Browser testing with Vitest
- **@vitest/coverage-v8** - Code coverage reporting

### Build Tools
- **@vitejs/plugin-vue** - Vue 3 plugin for Vite

## 📁 Storybook Configuration

### Directory Structure
```
x01-FrontEnd/x0101-xMixing_Nuxt/
├── .storybook/
│   ├── main.ts              # Main configuration
│   ├── preview.ts           # Preview configuration
│   └── vitest.setup.ts      # Vitest setup
├── stories/                 # Example stories (auto-generated)
│   ├── Button.vue
│   ├── Button.stories.ts
│   ├── Header.vue
│   ├── Header.stories.ts
│   └── ...
└── app/
    └── components/          # Your components (add .stories.ts files here)
```

### Configuration Files

#### `.storybook/main.ts`
- Configured for Vue 3 + Vite
- Includes Vue plugin for proper .vue file parsing
- Story locations:
  - `../stories/**/*.stories.@(js|jsx|mjs|ts|tsx)`
  - `../app/components/**/*.stories.@(js|jsx|mjs|ts|tsx)` (for your components)

#### `.storybook/preview.ts`
- Global parameters for all stories
- Accessibility testing enabled
- Light/dark background themes

## 📝 Creating Stories

### Example: Button Component Story

Create a file: `app/components/MyButton.stories.ts`

```typescript
import type { Meta, StoryObj } from '@storybook/vue3'
import MyButton from './MyButton.vue'

const meta: Meta<typeof MyButton> = {
  title: 'Components/MyButton',
  component: MyButton,
  tags: ['autodocs'],
  argTypes: {
    label: { control: 'text' },
    onClick: { action: 'clicked' }
  }
}

export default meta
type Story = StoryObj<typeof MyButton>

export const Primary: Story = {
  args: {
    label: 'Primary Button',
    primary: true
  }
}

export const Secondary: Story = {
  args: {
    label: 'Secondary Button',
    primary: false
  }
}
```

### Example: Quasar Component Story

For Quasar components (q-btn, q-input, etc.):

```typescript
import type { Meta, StoryObj } from '@storybook/vue3'
import { QBtn } from 'quasar'

const meta: Meta<typeof QBtn> = {
  title: 'Quasar/Button',
  component: QBtn,
  tags: ['autodocs']
}

export default meta
type Story = StoryObj<typeof QBtn>

export const Default: Story = {
  args: {
    label: 'Click Me',
    color: 'primary'
  }
}
```

## 🎨 Features Enabled

### 1. **Visual Testing** (@chromatic-com/storybook)
- Capture visual snapshots of components
- Detect visual regressions

### 2. **Accessibility Testing** (@storybook/addon-a11y)
- Automatic a11y checks
- WCAG compliance testing
- Currently set to 'todo' mode (shows violations without failing)

### 3. **Component Testing** (@storybook/addon-vitest)
- Write tests alongside stories
- Run tests in the browser
- Integration with Vitest

### 4. **Auto Documentation** (@storybook/addon-docs)
- Auto-generated component documentation
- Props table generation
- Usage examples

### 5. **Interactive Onboarding** (@storybook/addon-onboarding)
- Guided tour for new users
- Best practices and tips

## 🧪 Testing with Vitest

Storybook includes Vitest integration. Run tests with:

```bash
npm run test
```

Configuration file: `vitest.config.ts`

## 📊 Scripts Added to package.json

```json
{
  "scripts": {
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build"
  }
}
```

## 🔧 Customization

### Adding More Addons

```bash
npm install -D @storybook/addon-[addon-name]
```

Then add to `.storybook/main.ts`:
```typescript
addons: [
  // ... existing addons
  "@storybook/addon-[addon-name]"
]
```

### Configuring Quasar (Advanced)

To use Quasar components in stories, you'll need to:

1. Import Quasar styles in your stories
2. Configure Quasar plugins as needed
3. Use Quasar components directly

## 📚 Resources

- **Storybook Docs**: https://storybook.js.org/docs
- **Vue 3 Guide**: https://storybook.js.org/docs/vue/get-started/introduction
- **Addons**: https://storybook.js.org/addons
- **Discord Community**: https://discord.gg/storybook/

## 🎯 Next Steps

1. **Explore Example Stories**: Check out the auto-generated stories in the `stories/` folder
2. **Create Your First Story**: Add a `.stories.ts` file for one of your components
3. **Run Accessibility Tests**: Use the a11y addon to check component accessibility
4. **Build Storybook**: Run `npm run build-storybook` to create a static build
5. **Deploy**: Deploy the built Storybook to share with your team

## 🐛 Troubleshooting

### Quasar Components Not Working
If you need full Quasar support in Storybook, you may need to:
- Install Quasar as a dependency (already installed)
- Configure Quasar plugins in preview.ts
- Import Quasar styles

### Port Already in Use
If port 6006 is in use, specify a different port:
```bash
npm run storybook -- -p 6007
```

## 💡 Tips

- Use the **Controls** addon to interactively test component props
- Use the **Actions** addon to log component events
- Use the **Docs** tab to see auto-generated documentation
- Press `A` to toggle the addons panel
- Press `D` to toggle dark mode
- Press `F` to toggle fullscreen

---

**Storybook is ready!** Start building and documenting your components in isolation. 🎉
