/**
 * Filter state types for political influence data
 * Used across all islands for synchronized filtering
 */

// Donor types - person or specific organization classifications
export type DonorType = 'person' | 'trade-union' | 'company' | 'organization';
export type ActorType = 'person' | 'organization';

export interface FilterState {
  // Date range filters
  dateFrom?: string; // YYYY-MM-DD format
  dateTo?: string;   // YYYY-MM-DD format

  // Value filters
  minValue?: number;
  maxValue?: number;

  // Type filters
  donorType?: DonorType;
  recipientType?: ActorType;

  // Exclusion filters
  excludeDonorType?: DonorType;

  // Special filters
  hasLobbying?: boolean; // Show only donors who also lobby

  // Pagination
  page: number;
  limit: number;

  // Search
  query?: string;
}

export const DEFAULT_FILTER_STATE: FilterState = {
  page: 1,
  limit: 20,
};

/**
 * URL parameter mapping
 * Maps FilterState keys to URL parameter names
 */
export const URL_PARAM_MAP = {
  dateFrom: 'date_from',
  dateTo: 'date_to',
  minValue: 'min_value',
  maxValue: 'max_value',
  donorType: 'donor_type',
  excludeDonorType: 'exclude_donor_type',
  recipientType: 'recipient_type',
  hasLobbying: 'has_lobbying',
  page: 'page',
  limit: 'limit',
  query: 'q',
} as const;
