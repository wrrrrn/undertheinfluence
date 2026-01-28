import React, { useEffect, useState } from 'react';
import { useFilterStore } from '../store/filterStore';
import { useDebounce } from '../hooks/useDebounce';
import { useParties } from '../hooks/useParties';
import styles from './PoliticianFilters.module.scss';

export const PoliticianFilters = () => {
  const { query, roleType, partyId, govtStatus, setFilter, resetFilters } = useFilterStore();
  const { data: parties } = useParties();
  const [localSearch, setLocalSearch] = useState(query || '');
  const debouncedSearch = useDebounce(localSearch, 300);

  // Sync debounced search to store
  useEffect(() => {
    if (debouncedSearch !== query) {
      setFilter({ query: debouncedSearch }, { resetPage: true });
    }
  }, [debouncedSearch, query, setFilter]);

  // Sync store changes back to local input (e.g. back button)
  useEffect(() => {
    if (query !== undefined && query !== localSearch) {
      setLocalSearch(query);
    }
  }, [query]);

  const handleRoleChange = (role: 'mp' | 'lord' | 'minister' | undefined) => {
    setFilter({ roleType: role === roleType ? undefined : role }, { resetPage: true });
  };

  const handleStatusChange = (status: 'government' | 'opposition' | undefined) => {
    setFilter({ govtStatus: status === govtStatus ? undefined : status }, { resetPage: true });
  };

  const handlePartyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value ? Number(e.target.value) : undefined;
    setFilter({ partyId: value }, { resetPage: true });
  };

  return (
    <div className={styles.sidebar}>
      {/* Search */}
      <div className={styles.searchWrapper}>
        <i className={`bi bi-search ${styles.searchIcon}`}></i>
        <input
          type="search"
          className={styles.searchInput}
          placeholder="Search by name..."
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
        />
      </div>

      {/* Role */}
      <div className={styles.section}>
        <h6 className={styles.sectionTitle}>Role</h6>
        <div className={styles.buttonGroup}>
          <button
            className={`${styles.filterButton} ${!roleType ? styles.active : ''}`}
            onClick={() => handleRoleChange(undefined)}
          >
            All Roles
          </button>
          <button
            className={`${styles.filterButton} ${roleType === 'mp' ? styles.active : ''}`}
            onClick={() => handleRoleChange('mp')}
          >
            MPs
          </button>
          <button
            className={`${styles.filterButton} ${roleType === 'lord' ? styles.active : ''}`}
            onClick={() => handleRoleChange('lord')}
          >
            Peers (Lords)
          </button>
          <button
            className={`${styles.filterButton} ${roleType === 'minister' ? styles.active : ''}`}
            onClick={() => handleRoleChange('minister')}
          >
            Ministers
          </button>
        </div>
      </div>

      {/* Government Status */}
      <div className={styles.section}>
        <h6 className={styles.sectionTitle}>Status</h6>
        <div className={styles.buttonGroup}>
          <button
            className={`${styles.filterButton} ${!govtStatus ? styles.active : ''}`}
            onClick={() => handleStatusChange(undefined)}
          >
            Any Status
          </button>
          <button
            className={`${styles.filterButton} ${govtStatus === 'government' ? styles.active : ''}`}
            onClick={() => handleStatusChange('government')}
          >
            Government
          </button>
          <button
            className={`${styles.filterButton} ${govtStatus === 'opposition' ? styles.active : ''}`}
            onClick={() => handleStatusChange('opposition')}
          >
            Opposition
          </button>
        </div>
      </div>

      {/* Party */}
      <div className={styles.section}>
        <h6 className={styles.sectionTitle}>Party</h6>
        <select 
          className={styles.select}
          value={partyId || ''}
          onChange={handlePartyChange}
        >
          <option value="">All Parties</option>
          {parties?.map(party => (
            <option key={party.id} value={party.id}>
              {party.name} ({party.mp_count + party.lord_count})
            </option>
          ))}
        </select>
      </div>

      {/* Reset */}
      <div className="mt-4 pt-3 border-top">
        <button
          className="btn btn-outline-secondary btn-sm w-100"
          onClick={resetFilters}
        >
          Reset Filters
        </button>
      </div>
    </div>
  );
};
