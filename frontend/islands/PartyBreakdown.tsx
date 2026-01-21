/**
 * PartyBreakdown - Displays donation breakdown by political party
 * Fetches from /api/v2/aggregates/party-donations/ and renders PartyCard grid
 * Automatically updates when filters change
 */

import React from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { PartyCard } from '../components/PartyCard';
import { useFilterStore } from '../store/filterStore';
import styles from './PartyBreakdown.module.scss';

const queryClient = new QueryClient();

interface Party {
  id: number;
  name: string;
  actor_type: string;
  classification: string;
}

interface PartyDonation {
  party: Party;
  total_received: number;
  donation_count: number;
  donor_count: number;
}

interface PartyBreakdownInnerProps {
  limit?: number;
  apiUrl?: string;
  compact?: boolean;
}

function usePartyDonations(apiUrl: string, limit: number) {
  const filters = useFilterStore();

  // Build query parameters from filter state
  const queryParams = new URLSearchParams();
  queryParams.set('limit', String(limit));

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
  const url = `${apiUrl}?${queryString}`;

  return useQuery({
    queryKey: ['party-donations', queryString],
    queryFn: async () => {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch party donations');
      }
      const data = await response.json();
      return data.results as PartyDonation[];
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

function PartyBreakdownInner({
  limit = 10,
  apiUrl = '/api/v2/aggregates/party-donations/',
  compact = false,
}: PartyBreakdownInnerProps) {
  const { data, isLoading, error } = usePartyDonations(apiUrl, limit);

  if (error) {
    return (
      <div className={styles.error}>
        <strong>Failed to load party breakdown</strong>
        <p>{error instanceof Error ? error.message : 'Unknown error'}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading party breakdown...</span>
        </div>
        <p>Loading party donations...</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No party donation data available.</p>
      </div>
    );
  }

  return (
    <div className={styles.partyBreakdown}>
      <div className={styles.grid}>
        {data.map((partyData) => (
          <div key={partyData.party.id} className={styles.gridItem}>
            <PartyCard
              name={partyData.party.name}
              totalReceived={partyData.total_received}
              donationCount={partyData.donation_count}
              donorCount={partyData.donor_count}
              partyId={partyData.party.id}
              compact={compact}
            />
          </div>
        ))}
      </div>

      <div className={styles.footer}>
        <a href="/explore/?recipient_type=party" className={styles.viewAllLink}>
          View all party donations →
        </a>
      </div>
    </div>
  );
}

export default function PartyBreakdown(props: PartyBreakdownInnerProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <PartyBreakdownInner {...props} />
    </QueryClientProvider>
  );
}
