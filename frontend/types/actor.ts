/**
 * Actor types for political influence data
 * Based on Popolo specification used in the backend
 */

export type ActorType = 'person' | 'organization';

export interface Actor {
  id: number;
  name: string;
  actor_type: ActorType;
  classification?: string; // e.g., "MP", "Political Party", "Trade Union"
  image?: string;
}

export interface ActorStats {
  totalDonated?: number;
  totalReceived?: number;
  donationCount?: number;
  isLobbyingClient?: boolean;
  isDonor?: boolean;
}

export interface ActorCardProps {
  actor: Actor;
  stats?: ActorStats;
  compact?: boolean;
  showStats?: boolean;
  onClick?: () => void;
}

/**
 * Format currency in GBP
 */
export function formatCurrency(amount: number): string {
  if (amount >= 1_000_000) {
    return `£${(amount / 1_000_000).toFixed(1)}M`;
  } else if (amount >= 1_000) {
    return `£${(amount / 1_000).toFixed(1)}K`;
  } else {
    return `£${amount.toLocaleString('en-GB')}`;
  }
}

/**
 * Get profile URL for an actor
 */
export function getActorProfileUrl(actor: Actor): string {
  return actor.actor_type === 'person'
    ? `/person/${actor.id}/`
    : `/organization/${actor.id}/`;
}
