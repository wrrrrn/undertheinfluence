import React from 'react';
import styles from './PoliticianCard.module.scss';

export interface Politician {
  id: number;
  name: string;
  image?: string;
  current_party?: {
    id: number;
    name: string;
  };
  current_role?: {
    title: string;
    start_date: string;
    type: string;
  };
  is_minister: boolean;
  ministerial_role?: string;
  stats?: {
    total_donations_received: number;
  };
}

interface PoliticianCardProps {
  politician: Politician;
}

// Helper to get colors based on party name
const getPartyColors = (partyName?: string) => {
  const normalized = partyName?.toLowerCase() || '';
  if (normalized.includes('labour')) return { color: 'var(--party-lab)', bg: '#fee2e2', text: '#B0002E' };
  if (normalized.includes('conservative')) return { color: 'var(--party-con)', bg: '#e0f2fe', text: '#005B94' };
  if (normalized.includes('lib') && normalized.includes('dem')) return { color: 'var(--party-lib)', bg: '#fef3c7', text: '#A86500' };
  if (normalized.includes('green')) return { color: 'var(--party-grn)', bg: '#dcfce7', text: '#3D6E0E' };
  if (normalized.includes('reform')) return { color: 'var(--party-ref)', bg: '#cffafe', text: '#0C7A8B' };
  if (normalized.includes('scottish national') || normalized.includes('snp')) return { color: 'var(--party-snp)', bg: '#fef9c3', text: '#8B8200' };
  
  return { color: 'var(--bs-gray-400)', bg: 'var(--bs-gray-100)', text: 'var(--bs-gray-700)' };
};

export const PoliticianCard: React.FC<PoliticianCardProps> = ({ politician }) => {
  const partyColors = getPartyColors(politician.current_party?.name);
  const [imgError, setImgError] = React.useState(false);
  
  const style = {
    '--party-color': partyColors.color,
    '--party-bg': partyColors.bg,
    '--party-text': partyColors.text,
  } as React.CSSProperties;

  return (
    <a href={`/person/${politician.id}/`} className={styles.card} style={style}>
      <div className={styles.header}>
        {politician.image && !imgError ? (
          <img 
            src={politician.image} 
            alt={politician.name}
            className={styles.avatar}
            onError={() => setImgError(true)}
          />
        ) : (
          <div className={`${styles.avatar} d-flex align-items-center justify-content-center bg-light text-secondary`}>
            <i className="bi bi-person-fill fs-3"></i>
          </div>
        )}
        <div className={styles.info}>
          <h3 className={styles.name}>{politician.name}</h3>
          <div className={styles.role}>
            {politician.ministerial_role || politician.current_role?.title || 'Politician'}
          </div>
        </div>
      </div>

      <div className={styles.badges}>
        {politician.current_party && (
          <span className={`${styles.badge} ${styles.party}`}>
            {politician.current_party.name}
          </span>
        )}
        {politician.is_minister && (
          <span className={`${styles.badge} ${styles.minister}`}>
            Minister
          </span>
        )}
      </div>

      {politician.stats && (
        <div className={styles.stats}>
          <span className={styles.statLabel}>Total Donations</span>
          <span className={styles.statValue}>
            £{(politician.stats.total_donations_received || 0).toLocaleString()}
          </span>
        </div>
      )}
    </a>
  );
};
