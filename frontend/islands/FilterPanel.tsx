/**
 * FilterPanel - Interactive filter controls for political influence data
 * Uses Zustand store for state management and URL synchronization
 */

import React from 'react';
import { useFilterStore } from '../store/filterStore';
import { DonorType } from '../types/filters';
import styles from './FilterPanel.module.scss';

export default function FilterPanel() {
  const {
    dateFrom,
    dateTo,
    minValue,
    donorType,
    hasLobbying,
    setFilter,
    resetFilters,
  } = useFilterStore();

  const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ dateFrom: e.target.value || undefined }, { resetPage: true });
  };

  const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ dateTo: e.target.value || undefined }, { resetPage: true });
  };

  const handleMinValueChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value ? Number(e.target.value) : undefined;
    setFilter({ minValue: value }, { resetPage: true });
  };

  const handleDonorTypeToggle = (type: DonorType) => {
    setFilter({ donorType: donorType === type ? undefined : type }, { resetPage: true });
  };

  const handleHasLobbyingChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ hasLobbying: e.target.checked || undefined }, { resetPage: true });
  };

  const handleReset = () => {
    resetFilters();
  };

  // Check if any filters are active
  const hasActiveFilters = !!(
    dateFrom ||
    dateTo ||
    minValue ||
    donorType ||
    hasLobbying
  );

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3 className={styles.title}>Filters</h3>
        {hasActiveFilters && (
          <button
            type="button"
            className={styles.resetButton}
            onClick={handleReset}
          >
            Clear All
          </button>
        )}
      </div>

      <div className={styles.body}>
        {/* Date Range */}
        <div className={styles.section}>
          <label className={styles.label}>Date Range</label>
          <div className={styles.dateRange}>
            <div className={styles.dateInput}>
              <label className={styles.dateLabel}>From</label>
              <input
                type="date"
                className={styles.input}
                value={dateFrom || ''}
                onChange={handleDateFromChange}
                max={dateTo || undefined}
              />
            </div>
            <div className={styles.dateInput}>
              <label className={styles.dateLabel}>To</label>
              <input
                type="date"
                className={styles.input}
                value={dateTo || ''}
                onChange={handleDateToChange}
                min={dateFrom || undefined}
              />
            </div>
          </div>
        </div>

        {/* Minimum Value */}
        <div className={styles.section}>
          <label className={styles.label} htmlFor="minValue">
            Minimum Value
          </label>
          <select
            id="minValue"
            className={styles.select}
            value={minValue || ''}
            onChange={handleMinValueChange}
          >
            <option value="">Any amount</option>
            <option value="1000">£1,000+</option>
            <option value="10000">£10,000+</option>
            <option value="100000">£100,000+</option>
            <option value="1000000">£1,000,000+</option>
          </select>
        </div>

        {/* Donor Type */}
        <div className={styles.section}>
          <label className={styles.label}>Donor Type</label>
          <div className={styles.chipGroup}>
            {(['individual', 'organization', 'trade-union', 'company'] as DonorType[]).map(
              (type) => (
                <button
                  key={type}
                  type="button"
                  className={`${styles.chip} ${donorType === type ? styles.chipActive : ''}`}
                  onClick={() => handleDonorTypeToggle(type)}
                >
                  {type === 'trade-union' ? 'Trade Union' : type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              )
            )}
          </div>
        </div>

        {/* Has Lobbying */}
        <div className={styles.section}>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={hasLobbying || false}
              onChange={handleHasLobbyingChange}
            />
            <span>Only donors who also lobby</span>
          </label>
        </div>
      </div>
    </div>
  );
}
