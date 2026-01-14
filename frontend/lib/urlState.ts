/**
 * URL state synchronization utilities
 * Handles parsing and serializing filter state to/from URL parameters
 */

import { FilterState, DEFAULT_FILTER_STATE, URL_PARAM_MAP } from '../types/filters';

/**
 * Parse current URL parameters into FilterState
 */
export function parseUrlParams(): FilterState {
  const params = new URLSearchParams(window.location.search);
  const state: FilterState = { ...DEFAULT_FILTER_STATE };

  // Date filters
  const dateFrom = params.get(URL_PARAM_MAP.dateFrom);
  if (dateFrom) state.dateFrom = dateFrom;

  const dateTo = params.get(URL_PARAM_MAP.dateTo);
  if (dateTo) state.dateTo = dateTo;

  // Value filters
  const minValue = params.get(URL_PARAM_MAP.minValue);
  if (minValue) state.minValue = Number(minValue);

  const maxValue = params.get(URL_PARAM_MAP.maxValue);
  if (maxValue) state.maxValue = Number(maxValue);

  // Type filters
  const donorType = params.get(URL_PARAM_MAP.donorType);
  if (donorType) state.donorType = donorType as FilterState['donorType'];

  const recipientType = params.get(URL_PARAM_MAP.recipientType);
  if (recipientType) state.recipientType = recipientType as FilterState['recipientType'];

  // Special filters
  const hasLobbying = params.get(URL_PARAM_MAP.hasLobbying);
  if (hasLobbying) state.hasLobbying = hasLobbying === 'true';

  // Pagination
  const page = params.get(URL_PARAM_MAP.page);
  if (page) state.page = Number(page);

  const limit = params.get(URL_PARAM_MAP.limit);
  if (limit) state.limit = Number(limit);

  // Search
  const query = params.get(URL_PARAM_MAP.query);
  if (query) state.query = query;

  return state;
}

/**
 * Serialize FilterState to URL parameters
 */
export function serializeFilterState(state: FilterState): URLSearchParams {
  const params = new URLSearchParams();

  // Only add parameters that differ from defaults
  if (state.dateFrom) params.set(URL_PARAM_MAP.dateFrom, state.dateFrom);
  if (state.dateTo) params.set(URL_PARAM_MAP.dateTo, state.dateTo);
  if (state.minValue !== undefined) params.set(URL_PARAM_MAP.minValue, String(state.minValue));
  if (state.maxValue !== undefined) params.set(URL_PARAM_MAP.maxValue, String(state.maxValue));
  if (state.donorType) params.set(URL_PARAM_MAP.donorType, state.donorType);
  if (state.recipientType) params.set(URL_PARAM_MAP.recipientType, state.recipientType);
  if (state.hasLobbying !== undefined) params.set(URL_PARAM_MAP.hasLobbying, String(state.hasLobbying));
  if (state.page !== 1) params.set(URL_PARAM_MAP.page, String(state.page));
  if (state.limit !== 20) params.set(URL_PARAM_MAP.limit, String(state.limit));
  if (state.query) params.set(URL_PARAM_MAP.query, state.query);

  return params;
}

/**
 * Update URL without triggering page reload
 * @param state - New filter state
 * @param replace - Use replaceState instead of pushState (default: false)
 */
export function updateUrl(state: FilterState, replace: boolean = false): void {
  const params = serializeFilterState(state);
  const url = params.toString()
    ? `${window.location.pathname}?${params.toString()}`
    : window.location.pathname;

  if (replace) {
    window.history.replaceState({}, '', url);
  } else {
    window.history.pushState({}, '', url);
  }
}
