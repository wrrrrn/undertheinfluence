// Islands Architecture - Island Loader
// This file detects and hydrates all React islands on the page

import { createRoot } from 'react-dom/client';

// Island registry (lazy-loaded for code splitting)
const islands: Record<string, () => Promise<{ default: React.ComponentType<any> }>> = {
  // Islands will be added here as we build them
  // Example: 'SearchBar': () => import('./islands/SearchBar'),
};

// Hydrate all islands on page load
document.addEventListener('DOMContentLoaded', async () => {
  const islandElements = document.querySelectorAll('[data-island]');

  console.log(`Found ${islandElements.length} islands to hydrate`);

  for (const el of islandElements) {
    const islandName = el.getAttribute('data-island');

    if (!islandName) {
      console.warn('Island element missing data-island attribute');
      continue;
    }

    const loader = islands[islandName];

    if (!loader) {
      console.warn(`Unknown island: ${islandName}`);
      continue;
    }

    try {
      const { default: Component } = await loader();

      // Extract data-* attributes as props
      const props = { ...el.dataset };
      delete props.island; // Remove the island name from props

      // Hydrate the island
      const root = createRoot(el);
      root.render(<Component {...props} />);

      console.log(`Hydrated island: ${islandName}`);
    } catch (err) {
      console.error(`Failed to load island ${islandName}:`, err);
    }
  }
});
