import React from 'react';
import { usePoliticians } from '../hooks/usePoliticians';
import { useFilterStore } from '../store/filterStore';
import { PoliticianCard } from './PoliticianCard';
import styles from './PoliticianList.module.scss';

export const PoliticianList = () => {
  const { data, isLoading, isError } = usePoliticians();
  const { page, setFilter } = useFilterStore();

  if (isLoading) {
    return (
      <div className={styles.loader}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="alert alert-danger" role="alert">
        Failed to load politicians. Please try again later.
      </div>
    );
  }

  if (!data?.results.length) {
    return (
      <div className={styles.emptyState}>
        <h3>No politicians found</h3>
        <p>Try adjusting your search or filters.</p>
      </div>
    );
  }

  const totalPages = Math.ceil(data.count / 20); // Assuming limit 20

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="text-muted mb-0">
          Showing {data.results.length} of {data.count.toLocaleString()} politicians
        </h5>
      </div>

      <div className={styles.grid}>
        {data.results.map((politician) => (
          <PoliticianCard key={politician.id} politician={politician} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageButton}
            disabled={page === 1}
            onClick={() => setFilter({ page: page - 1 })}
          >
            Previous
          </button>
          
          <span className="align-self-center text-muted">
            Page {page} of {totalPages}
          </span>

          <button
            className={styles.pageButton}
            disabled={page >= totalPages}
            onClick={() => setFilter({ page: page + 1 })}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
