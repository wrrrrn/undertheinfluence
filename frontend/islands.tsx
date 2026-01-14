// Islands Architecture - Island Loader
// This file detects and hydrates all React islands on the page

import { createRoot } from 'react-dom/client';
import { Component, ErrorInfo, ReactNode } from 'react';
import { initializeFilterStore } from './store/filterStore';

/**
 * Error Boundary component for island hydration failures
 */
class IslandErrorBoundary extends Component<
  { children: ReactNode; islandName: string },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: ReactNode; islandName: string }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Island ${this.props.islandName} error:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="island-error">
          <strong>Failed to load {this.props.islandName}</strong>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Island registry (lazy-loaded for code splitting)
 * Add new islands here as we build them
 */
const islands: Record<string, () => Promise<{ default: React.ComponentType<any> }>> = {
  // Example: 'SearchBar': () => import('./islands/SearchBar'),
  // Example: 'FilterPanel': () => import('./islands/FilterPanel'),
};

/**
 * Initialize island hydration system
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize global filter store from URL
  initializeFilterStore();
  console.log('✓ Filter store initialized from URL');

  // Find and hydrate all islands
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

      // Hydrate the island with error boundary
      const root = createRoot(el);
      root.render(
        <IslandErrorBoundary islandName={islandName}>
          <Component {...props} />
        </IslandErrorBoundary>
      );

      console.log(`✓ Hydrated island: ${islandName}`);
    } catch (err) {
      console.error(`✗ Failed to load island ${islandName}:`, err);

      // Show error UI in the island container
      const root = createRoot(el);
      root.render(
        <div className="island-error">
          <strong>Failed to load {islandName}</strong>
          <p>{err instanceof Error ? err.message : 'Unknown error'}</p>
        </div>
      );
    }
  }
});
