/* @refresh reset */
/**
 * ActorCard - Universal component for displaying people and organizations
 * Used in leaderboards, search results, and embedded in editorial content
 */

import React from 'react';
import { ActorCardProps, formatCurrency, getActorProfileUrl } from '../types/actor';
import styles from './ActorCard.module.scss';

export default function ActorCard({
  actor,
  stats,
  compact = false,
  showStats = true,
  onClick,
}: ActorCardProps) {
  const profileUrl = getActorProfileUrl(actor);

  // Compact mode: Single line with minimal info
  if (compact) {
    return (
      <a
        href={profileUrl}
        className={`${styles.card} ${styles.compact}`}
        onClick={onClick}
      >
        {actor.image && (
          <img
            src={actor.image}
            alt={actor.name}
            className={styles.image}
          />
        )}
        <div className={styles.content}>
          <h3 className={styles.name}>{actor.name}</h3>
          <p className={styles.classification}>
            {actor.classification || actor.actor_type}
          </p>
        </div>
        {showStats && stats?.totalDonated && (
          <span className={styles.statBadge}>
            {formatCurrency(stats.totalDonated)}
          </span>
        )}
      </a>
    );
  }

  // Full card mode: More detailed display
  return (
    <div className={styles.card} onClick={onClick}>
      <a href={profileUrl} className={styles.cardLink}>
        {actor.image && (
          <div className={styles.imageWrapper}>
            <img
              src={actor.image}
              alt={actor.name}
              className={styles.imageFull}
            />
          </div>
        )}

        <div className={styles.contentFull}>
          <h3 className={styles.nameFull}>{actor.name}</h3>

          <p className={styles.classificationFull}>
            {actor.classification || actor.actor_type}
          </p>

          {showStats && stats && (
            <div className={styles.stats}>
              {stats.totalDonated !== undefined && (
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Donated:</span>
                  <span className={styles.statValue}>
                    {formatCurrency(stats.totalDonated)}
                  </span>
                </div>
              )}

              {stats.totalReceived !== undefined && (
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Received:</span>
                  <span className={styles.statValue}>
                    {formatCurrency(stats.totalReceived)}
                  </span>
                </div>
              )}

              {stats.donationCount !== undefined && (
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Donations:</span>
                  <span className={styles.statValue}>
                    {stats.donationCount}
                  </span>
                </div>
              )}

              {stats.isLobbyingClient && (
                <span className={styles.badge}>
                  Also lobbies
                </span>
              )}
            </div>
          )}
        </div>
      </a>
    </div>
  );
}
