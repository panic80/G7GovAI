import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: env.VITE_RAG_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
          configure: (proxy, _options) => {
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              // Inject the secret key from the server-side env vars
              // This keeps the key out of the browser bundle
              const apiKey = env.VITE_GOVAI_API_KEY || env.GOVAI_API_KEY || '';
              if (apiKey) {
                proxyReq.setHeader('X-GovAI-Key', apiKey);
              }
              // Disable buffering for streaming responses
              proxyReq.setHeader('X-Accel-Buffering', 'no');
            });
            // Handle streaming responses properly
            proxy.on('proxyRes', (proxyRes, req, res) => {
              // Disable buffering for ndjson streaming responses
              if (proxyRes.headers['content-type']?.includes('ndjson')) {
                proxyRes.headers['cache-control'] = 'no-cache';
                proxyRes.headers['x-accel-buffering'] = 'no';
              }
            });
          },
        },
      },
    },
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    }
  };
});