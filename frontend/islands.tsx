// Islands Architecture - Island Loader
// This file detects and hydrates all React islands on the page

import { createRoot } from 'react-dom/client';
import { Component, ErrorInfo, ReactNode } from 'react';
import { initializeFilterStore } from './store/filterStore';

// TypeScript declarations for React Fast Refresh globals
declare global {
  interface Window {
    $RefreshReg$?: any;
    $RefreshSig$?: any;
  }
}

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
  'ActorCard': () => import('./components/ActorCard'),
  'FilterPanel': () => import('./islands/FilterPanel'),
  'TopDonorsLeaderboard': () => import('./islands/TopDonorsLeaderboard'),
  'ConcentrationChart': () => import('./islands/ConcentrationChart'),
  'StatsGrid': () => import('./islands/StatsGrid'),
  'PartyBreakdown': () => import('./islands/PartyBreakdown'),
};

/**
 * Wait for React Fast Refresh runtime to be ready
 * This is needed for Vite's HMR with React
 */
async function waitForReactRefresh(): Promise<void> {
  const maxWait = 5000; // 5 seconds max
  const startTime = Date.now();

  while (!window.$RefreshReg$ || !window.$RefreshSig$) {
    if (Date.now() - startTime > maxWait) {
      console.warn('React Fast Refresh runtime not detected after 5s, proceeding anyway');
      break;
    }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
}

/**
 * Initialize island hydration system
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize global filter store from URL
  initializeFilterStore();
  console.log('✓ Filter store initialized from URL');

  // Wait for React Fast Refresh runtime to be ready
  await waitForReactRefresh();
  console.log('✓ React Fast Refresh runtime ready');

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
      const rawProps = { ...el.dataset };
      delete rawProps.island; // Remove the island name from props

      // Parse JSON values from data attributes
      const props: Record<string, any> = {};
      for (const [key, value] of Object.entries(rawProps)) {
        // Try to parse as JSON first (for objects/arrays)
        if (value.startsWith('{') || value.startsWith('[')) {
          try {
            props[key] = JSON.parse(value);
          } catch {
            props[key] = value; // Keep as string if JSON parse fails
          }
        }
        // Parse boolean strings
        else if (value === 'true') props[key] = true;
        else if (value === 'false') props[key] = false;
        // Parse numbers
        else if (!isNaN(Number(value)) && value !== '') props[key] = Number(value);
        // Keep as string
        else props[key] = value;
      }

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
