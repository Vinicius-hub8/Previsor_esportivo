import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' deixa o site funcionar em qualquer subpasta (ex.: GitHub Pages).
export default defineConfig({
  plugins: [react()],
  base: './',
});
