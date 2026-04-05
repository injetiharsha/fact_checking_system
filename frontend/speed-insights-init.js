// Initialize Vercel Speed Insights
import { injectSpeedInsights } from './speed-insights.js';

// Inject Speed Insights when the page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    injectSpeedInsights();
  });
} else {
  // Document already loaded
  injectSpeedInsights();
}
