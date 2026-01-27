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
  recipientType?: 'person' | 'party' | 'organization';
  hasLobbying?: boolean;
  
  // Politician Directory specific
  roleType?: 'mp' | 'lord' | 'minister';
  partyId?: number;
  govtStatus?: 'government' | 'opposition' | 'other';
  
  page: number;
  limit: number;
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
  roleType: 'role_type',
  partyId: 'party',
  govtStatus: 'govt_status',
  page: 'page',
  limit: 'limit',
  query: 'q',
} as const;
