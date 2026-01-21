/**
 * Zustand store for filter state management
 * Automatically synchronizes with URL parameters
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { FilterState, DEFAULT_FILTER_STATE } from '../types/filters';
import { parseUrlParams, updateUrl } from '../lib/urlState';

interface FilterStore extends FilterState {
  // Actions
  setFilter: (updates: Partial<FilterState>, options?: { resetPage?: boolean }) => void;
  resetFilters: () => void;
  loadFromUrl: () => void;
}

/**
 * Global filter store
 * All islands subscribe to this store for synchronized state
 */
export const useFilterStore = create<FilterStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state from URL or defaults
    ...DEFAULT_FILTER_STATE,

    /**
     * Update filter state and sync to URL
     * @param updates - Partial state to update
     * @param options.resetPage - Reset page to 1 when filters change (default: false)
     */
    setFilter: (updates, options = {}) => {
      set((state) => {
        const newState: FilterState = {
          ...state,
          ...updates,
          // Reset page to 1 when filters change (unless page itself is being updated)
          page: options.resetPage && !('page' in updates) ? 1 : (updates.page ?? state.page),
        };

        // Sync to URL (replace state to avoid cluttering browser history)
        updateUrl(newState, true);

        return newState;
      });
    },

    /**
     * Reset all filters to defaults
     */
    resetFilters: () => {
      set(DEFAULT_FILTER_STATE);
      updateUrl(DEFAULT_FILTER_STATE, true);
    },

    /**
     * Load filter state from current URL
     * Called on initial page load and popstate events
     */
    loadFromUrl: () => {
      const urlState = parseUrlParams();
      set(urlState);
    },
  }))
);

/**
 * Initialize store from URL on page load
 * Call this once when the app initializes
 */
export function initializeFilterStore(): void {
  // Load initial state from URL
  useFilterStore.getState().loadFromUrl();

  // Listen for browser back/forward navigation
  window.addEventListener('popstate', () => {
    useFilterStore.getState().loadFromUrl();
  });
}

/**
 * Hook to subscribe to specific filter changes
 * @param selector - Function to select specific state slice
 * @example
 * const dateFrom = useFilterSelector(state => state.dateFrom);
 */
export function useFilterSelector<T>(selector: (state: FilterStore) => T): T {
  return useFilterStore(selector);
}
