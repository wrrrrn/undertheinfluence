/**
 * Types for donor concentration metrics
 */

export type ConcentrationCategory =
  | 'highly_concentrated'
  | 'moderately_concentrated'
  | 'dispersed'
  | 'no_data';

export interface ConcentrationMetrics {
  total_donors: number;
  total_donated: number;
  herfindahl_index: number; // 0-1, higher = more concentrated
  top_10_percent_share: number; // Percentage
  top_donor_share: number; // Percentage
  gini_coefficient: number; // 0-1, higher = more unequal
  concentration_category: ConcentrationCategory;
}
