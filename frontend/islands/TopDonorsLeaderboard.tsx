/**
 * TopDonorsLeaderboard - Interactive leaderboard consuming API v2
 * Automatically updates when filters change via Zustand store
 */

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTopDonors } from '../hooks/useTopDonors';
import { useFilterStore } from '../store/filterStore';
import ActorCard from '../components/ActorCard';
import { formatCurrency } from '../types/actor';
import styles from './TopDonorsLeaderboard.module.scss';

// Create a QueryClient instance for this island
const queryClient = new QueryClient();

interface TopDonorsLeaderboardInnerProps {
  limit?: number;
}

function TopDonorsLeaderboardInner({ limit = 20 }: TopDonorsLeaderboardInnerProps) {
  const { data, isLoading, error, isFetching } = useTopDonors(limit);
  const { page, setFilter } = useFilterStore();

  const handleNextPage = () => {
    setFilter({ page: page + 1 });
  };

  const handlePreviousPage = () => {
    setFilter({ page: Math.max(1, page - 1) });
  };

  if (error) {
    return (
      <div className={styles.error}>
        <strong>Failed to load leaderboard</strong>
        <p>{error instanceof Error ? error.message : 'Unknown error'}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner}></div>
        <p>Loading top donors...</p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No donors found matching your filters.</p>
        <p className="text-muted small">Try adjusting your filter criteria.</p>
      </div>
    );
  }

  return (
    <div className={styles.leaderboard}>
      <div className={styles.header}>
        <h3 className={styles.title}>
          Top Donors
          {isFetching && <span className={styles.refreshing}>Updating...</span>}
        </h3>
        <p className={styles.count}>
          {data.count.toLocaleString()} {data.count === 1 ? 'donor' : 'donors'} found
        </p>
      </div>

      <div className={styles.list}>
        {data.results.map((donor, index) => {
          // Calculate actual rank based on current page
          const rank = (page - 1) * limit + index + 1;
          return (
          <div key={donor.actor.id} className={styles.item}>
            <div className={styles.rank}>#{rank}</div>
            <div className={styles.card}>
              <ActorCard
                actor={{
                  id: donor.actor.id,
                  name: donor.actor.name,
                  actor_type: donor.actor.actor_type,
                  classification: donor.actor.classification,
                }}
                stats={{
                  totalDonated: donor.total_donated,
                  donationCount: donor.donation_count,
                  isLobbyingClient: donor.is_lobbying_client,
                }}
                compact={true}
                showStats={true}
              />
            </div>
          </div>
          );
        })}
      </div>

      {(data.next || data.previous) && (
        <div className={styles.pagination}>
          <button
            className={styles.paginationButton}
            disabled={!data.previous}
            onClick={handlePreviousPage}
          >
            Previous
          </button>
          <span className={styles.pageInfo}>Page {page}</span>
          <button
            className={styles.paginationButton}
            disabled={!data.next}
            onClick={handleNextPage}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default function TopDonorsLeaderboard(props: TopDonorsLeaderboardInnerProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <TopDonorsLeaderboardInner {...props} />
    </QueryClientProvider>
  );
}
