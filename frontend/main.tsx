// Main entry point for the application
// This file loads global styles and initializes the app
import './styles/main.scss';

console.log('UnderTheInfluence frontend loaded');
console.log('Vite HMR is enabled:', import.meta.hot ? 'YES ✅' : 'NO ❌');

// Add a visual indicator that Vite is working
if (import.meta.hot) {
  // Add a small badge to the page
  const badge = document.createElement('div');
  badge.id = 'vite-status-badge';
  badge.innerHTML = '⚡ Vite Dev Server Active';
  badge.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #646cff;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: bold;
    z-index: 9999;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  `;
  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(badge);
  });
}
