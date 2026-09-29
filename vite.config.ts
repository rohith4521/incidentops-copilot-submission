import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ command }) => {
  const isVercel = Boolean(process.env.VERCEL || process.env.NOW_BUILDER);
  return {
    base: isVercel ? '/' : (command === 'build' ? '/static/dist/' : '/'),
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: isVercel ? 'dist' : 'app/static/dist',
      emptyOutDir: true,
    },
  };
});
