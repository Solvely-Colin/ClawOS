import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './browser-tests',
  workers: 1,
  retries: 0,
  use: { browserName: 'chromium', headless: true },
  webServer: [
    { command: 'npm run dev -- --host 127.0.0.1 --port 5179 --strictPort', url: 'http://127.0.0.1:5179', reuseExistingServer: false },
    { command: 'npm run preview -- --host 127.0.0.1 --port 5180 --strictPort', url: 'http://127.0.0.1:5180', reuseExistingServer: false },
  ],
});
