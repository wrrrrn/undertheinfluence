/**
 * StatsGrid - Homepage key metrics display
 * Fetches live statistics from API and renders StatCard grid
 * Automatically updates when filters change
 */

import React from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { StatCard, StatCardVariant } from '../components/StatCard';
import { useFilterStore } from '../store/filterStore';
import styles from './StatsGrid.module.scss';

const queryClient = new QueryClient();

interface HomepageStats {
  total_donations: number;
  total_value: number;
  concentration_top_1_percent: number;
  concentration_donors_count: number;
  dual_influence_count: number;
  timestamp: string;
}

interface StatsGridInnerProps {
  apiUrl?: string;
}

function useHomepageStats(apiUrl: string = '/api/v2/aggregates/stats/') {
  const filters = useFilterStore();

  // Build query parameters from filter state
  const queryParams = new URLSearchParams();
  if (filters.dateFrom) {
    queryParams.set('received_after', filters.dateFrom.toISOString().split('T')[0]);
  }
  if (filters.dateTo) {
    queryParams.set('received_before', filters.dateTo.toISOString().split('T')[0]);
  }
  if (filters.minValue) {
    queryParams.set('value_min', String(filters.minValue));
  }
  if (filters.donorType) {
    queryParams.set('donor_type', filters.donorType);
  }

  const queryString = queryParams.toString();
  const url = queryString ? `${apiUrl}?${queryString}` : apiUrl;

  return useQuery({
    queryKey: ['homepage-stats', queryString],
    queryFn: async () => {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch homepage statistics');
      }
      return response.json() as Promise<HomepageStats>;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

function StatsGridInner({ apiUrl }: StatsGridInnerProps) {
  const { data, isLoading, error } = useHomepageStats(apiUrl);

  if (error) {
    return (
      <div className={styles.error}>
        <p>Failed to load statistics. Please try refreshing the page.</p>
      </div>
    );
  }

  // Format currency for display
  const formatCurrency = (value: number): string => {
    if (value >= 1_000_000_000) {
      return `£${(value / 1_000_000_000).toFixed(1)}B`;
    }
    if (value >= 1_000_000) {
      return `£${(value / 1_000_000).toFixed(1)}M`;
    }
    if (value >= 1_000) {
      return `£${(value / 1_000).toFixed(1)}K`;
    }
    return `£${value.toLocaleString()}`;
  };

  // Format number for display
  const formatNumber = (value: number): string => {
    return value.toLocaleString();
  };

  // Calculate concentration percentage
  const concentrationPercentage = data?.concentration_top_1_percent
    ? `${Math.round(data.concentration_top_1_percent * 100)}%`
    : '—';

  const concentrationDonors = data?.concentration_donors_count || 0;
  const concentrationSubtext = concentrationDonors > 0
    ? `${formatNumber(concentrationDonors)} donors control ${concentrationPercentage} of funding`
    : undefined;

  return (
    <div className={styles.statsGrid}>
      <StatCard
        value={data ? formatNumber(data.total_donations) : '—'}
        label="Donation Records"
        icon="database"
        timestamp={data?.timestamp}
        isLoading={isLoading}
        href="/explore/?sort=-value"
      />

      <StatCard
        value={data ? formatCurrency(data.total_value) : '—'}
        label="Total Donated"
        icon="currency-pound"
        timestamp={data?.timestamp}
        isLoading={isLoading}
        href="/explore/?sort=-value"
      />

      <StatCard
        value={concentrationPercentage}
        label="From Top 1.3%"
        subtext={concentrationSubtext}
        variant="danger"
        icon="exclamation-triangle"
        timestamp={data?.timestamp}
        isLoading={isLoading}
        href="/explore/?concentration=high"
      />

      <StatCard
        value={data ? formatNumber(data.dual_influence_count) : '—'}
        label="Dual Influence Orgs"
        subtext="Both donors & lobbyists"
        variant="warning"
        icon="arrow-left-right"
        timestamp={data?.timestamp}
        isLoading={isLoading}
        href="/explore/?dual_influence=true"
      />
    </div>
  );
}

export default function StatsGrid(props: StatsGridInnerProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <StatsGridInner {...props} />
    </QueryClientProvider>
  );
}
