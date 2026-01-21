/**
 * PartyCard - Display donation statistics for a political party
 * Uses official party colors with WCAG AA contrast considerations
 */

import React from 'react';
import styles from './PartyCard.module.scss';

export interface PartyCardProps {
  /** Party name (e.g., "Conservative Party", "Labour Party") */
  name: string;

  /** Total amount received by party */
  totalReceived: number;

  /** Number of donations */
  donationCount: number;

  /** Number of unique donors */
  donorCount: number;

  /** Optional party ID for linking */
  partyId?: number;

  /** Compact layout for smaller displays */
  compact?: boolean;
}

/**
 * Official UK political party color mappings
 * Note: Some colors (e.g., Lib Dem orange) may not meet WCAG AA contrast on white
 */
const PARTY_COLORS: Record<string, string> = {
  'Conservative': '#0087DC',     // Conservative blue
  'Labour': '#E4003B',           // Labour red
  'Liberal Democrat': '#FAA61A', // Lib Dem orange (⚠️ contrast warning)
  'Scottish National Party': '#FFF95D', // SNP yellow (⚠️ contrast warning)
  'Green Party': '#6AB023',      // Green
  'Plaid Cymru': '#005B54',      // Plaid teal
  'Democratic Unionist Party': '#D46A4C', // DUP orange
  'Sinn Féin': '#326760',        // Sinn Féin green
  'UK Independence Party': '#70147A', // UKIP purple
  'Brexit Party': '#12B6CF',     // Brexit Party cyan
  'Reform UK': '#12B6CF',        // Reform UK (successor to Brexit Party)
};

/**
 * Extract party short name from full organization name
 * "Conservative and Unionist Party" → "Conservative"
 */
function getPartyShortName(fullName: string): string {
  // Remove common suffixes
  const name = fullName
    .replace(/\s+(Party|and Unionist Party)$/i, '')
    .trim();

  // Special cases
  if (name.includes('Liberal Democrat')) return 'Liberal Democrat';
  if (name.includes('Scottish National')) return 'Scottish National Party';
  if (name.includes('Plaid Cymru')) return 'Plaid Cymru';

  return name;
}

/**
 * Get party color with fallback to gray
 */
function getPartyColor(partyName: string): string {
  const shortName = getPartyShortName(partyName);

  // Try exact match first
  if (PARTY_COLORS[shortName]) {
    return PARTY_COLORS[shortName];
  }

  // Try partial match
  for (const [key, color] of Object.entries(PARTY_COLORS)) {
    if (shortName.includes(key) || key.includes(shortName)) {
      return color;
    }
  }

  // Default gray for unknown parties
  return '#6c757d';
}

/**
 * Format currency for display
 */
function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) {
    return `£${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `£${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `£${(value / 1_000).toFixed(0)}K`;
  }
  return `£${value.toLocaleString()}`;
}

/**
 * Format number for display
 */
function formatNumber(value: number): string {
  return value.toLocaleString();
}

export function PartyCard({
  name,
  totalReceived,
  donationCount,
  donorCount,
  partyId,
  compact = false,
}: PartyCardProps) {
  const partyColor = getPartyColor(name);
  const avgDonation = donationCount > 0 ? totalReceived / donationCount : 0;

  const exploreUrl = partyId
    ? `/explore/?recipient=${partyId}`
    : `/explore/?recipient_name=${encodeURIComponent(name)}`;

  const cardClasses = [
    styles.partyCard,
    compact ? styles.compact : '',
  ].filter(Boolean).join(' ');

  return (
    <a href={exploreUrl} className={cardClasses}>
      <div
        className={styles.colorBar}
        style={{ backgroundColor: partyColor }}
        aria-hidden="true"
      />

      <div className={styles.content}>
        <h3 className={styles.partyName}>{getPartyShortName(name)}</h3>

        <div className={styles.stats}>
          <div className={styles.stat}>
            <div className={styles.statValue}>{formatCurrency(totalReceived)}</div>
            <div className={styles.statLabel}>Total Received</div>
          </div>

          {!compact && (
            <>
              <div className={styles.stat}>
                <div className={styles.statValue}>{formatNumber(donorCount)}</div>
                <div className={styles.statLabel}>Donors</div>
              </div>

              <div className={styles.stat}>
                <div className={styles.statValue}>{formatCurrency(avgDonation)}</div>
                <div className={styles.statLabel}>Avg Donation</div>
              </div>
            </>
          )}
        </div>
      </div>
    </a>
  );
}
