/**
 * StatCard - Display key metrics with optional live data fetching
 * Used for homepage metrics strip and editorial callouts
 */

import React from 'react';
import styles from './StatCard.module.scss';

export type StatCardVariant = 'default' | 'primary' | 'danger' | 'success' | 'warning';

export interface StatCardProps {
  /** The primary statistic value (e.g., "119,599" or "65%") */
  value: string;

  /** Short label describing the metric (e.g., "Donation Records") */
  label: string;

  /** Optional subtext providing additional context */
  subtext?: string;

  /** Visual variant for emphasis */
  variant?: StatCardVariant;

  /** Optional timestamp for data provenance ("Data as of" display) */
  timestamp?: string;

  /** Optional href to link the entire card */
  href?: string;

  /** Optional icon name (using Bootstrap Icons) */
  icon?: string;

  /** Whether to show a loading spinner */
  isLoading?: boolean;
}

const variantClasses: Record<StatCardVariant, string> = {
  default: styles.variantDefault,
  primary: styles.variantPrimary,
  danger: styles.variantDanger,
  success: styles.variantSuccess,
  warning: styles.variantWarning,
};

export function StatCard({
  value,
  label,
  subtext,
  variant = 'default',
  timestamp,
  href,
  icon,
  isLoading = false,
}: StatCardProps) {
  const cardClasses = [
    styles.statCard,
    variantClasses[variant],
    href ? styles.clickable : '',
  ].filter(Boolean).join(' ');

  const content = (
    <>
      {icon && (
        <div className={styles.icon}>
          <i className={`bi bi-${icon}`}></i>
        </div>
      )}

      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <div className="spinner-border spinner-border-sm" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : (
          <>
            <div className={styles.value}>{value}</div>
            <div className={styles.label}>{label}</div>
            {subtext && <div className={styles.subtext}>{subtext}</div>}
            {timestamp && (
              <div className={styles.timestamp}>
                Data as of {new Date(timestamp).toLocaleDateString('en-GB', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric'
                })}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );

  if (href) {
    return (
      <a href={href} className={cardClasses}>
        {content}
      </a>
    );
  }

  return <div className={cardClasses}>{content}</div>;
}
