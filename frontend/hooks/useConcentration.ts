/**
 * React Query hook for fetching donor concentration metrics from API v2
 * Automatically responds to filter state changes
 */

import { useQuery } from '@tanstack/react-query';
import { useFilterStore } from '../store/filterStore';
import { ConcentrationMetrics } from '../types/concentration';

export function useConcentration() {
  const filters = useFilterStore();

  // Build query parameters from filter state
  const queryParams = new URLSearchParams();

  if (filters.dateFrom) queryParams.set('received_after', filters.dateFrom);
  if (filters.dateTo) queryParams.set('received_before', filters.dateTo);
  if (filters.minValue) queryParams.set('value_min', String(filters.minValue));

  // Map donor type to API parameters
  if (filters.donorType) {
    if (filters.donorType === 'person') {
      queryParams.set('donor_type', 'person');
    } else if (filters.donorType === 'trade-union') {
      queryParams.set('donor_type', 'organization');
      queryParams.set('donor_classification', 'Trade Union');
    } else if (filters.donorType === 'company') {
      queryParams.set('donor_type', 'organization');
      queryParams.set('donor_classification', 'Company');
    } else if (filters.donorType === 'organization') {
      queryParams.set('donor_type', 'organization');
    }
  }

  // Map exclusion filter
  if (filters.excludeDonorType) {
    if (filters.excludeDonorType === 'trade-union') {
      queryParams.set('exclude_donor_classification', 'Trade Union');
    } else if (filters.excludeDonorType === 'company') {
      queryParams.set('exclude_donor_classification', 'Company');
    }
  }

  if (filters.hasLobbying) queryParams.set('has_lobbying', 'true');

  return useQuery<ConcentrationMetrics>({
    queryKey: ['concentration', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/aggregates/donor-concentration/?${queryParams}`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 1,
  });
}
