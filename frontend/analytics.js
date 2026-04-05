// Vercel Web Analytics and Speed Insights initialization
// This file should be loaded after the Vercel Analytics scripts
(function() {
  // Initialize Vercel Web Analytics
  // The analytics will be automatically injected when deployed to Vercel
  // For local development, this provides a no-op fallback
  
  if (typeof window !== 'undefined') {
    // Check if Vercel Analytics is available
    window.va = window.va || function () { 
      (window.vaq = window.vaq || []).push(arguments); 
    };
    
    // Check if Vercel Speed Insights is available
    window.si = window.si || function () { 
      (window.siq = window.siq || []).push(arguments); 
    };
  }
})();
