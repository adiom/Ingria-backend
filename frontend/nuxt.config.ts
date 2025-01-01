// nuxt.config.ts
export default defineNuxtConfig({
  devtools: { enabled: true },

  css: ['bootstrap/dist/css/bootstrap.min.css', '@/assets/css/main.css'],
  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
  ],
  tailwindcss: {
    cssPath: ['~/assets/css/tailwind.css', { injectPosition: "first" }],
    configPath: 'tailwind.config',
    exposeConfig: {
      level: 2
    },
    config: {},
    viewer: true,
  },

  vite: {
    optimizeDeps: {
      include: ['@popperjs/core'],
    },
  },

  compatibilityDate: '2024-12-23',
});