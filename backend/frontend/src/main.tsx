/**
 * Main entry point for MarketPrep frontend.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Register service worker for PWA support
import { registerSW } from 'virtual:pwa-register';

// Performance monitoring
import { setupPerformanceMonitoring } from './lib/performance';

// Setup performance monitoring in development
setupPerformanceMonitoring();

// Auto-update service worker when new version is available
const updateSW = registerSW({
  onNeedRefresh() {
    if (confirm('New version available! Reload to update?')) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.log('App ready to work offline');
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
