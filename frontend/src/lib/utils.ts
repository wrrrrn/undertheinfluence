export const API_URL = import.meta.env.DATA_API_URL || 'http://api:8000/api/v2';

export function formatCurrency(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (num >= 1_000_000_000) return `£${(num / 1_000_000_000).toFixed(1)}bn`;
  if (num >= 1_000_000) return `£${(num / 1_000_000).toFixed(1)}m`;
  if (num >= 1_000) return `£${(num / 1_000).toFixed(0)}k`;
  return `£${num.toLocaleString()}`;
}

export function formatDate(date: string | null): string {
  if (!date) return '—';
  if (date.length === 4) return date;
  if (date.length === 7) {
    const [y, m] = date.split('-');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[parseInt(m) - 1]} ${y}`;
  }
  return new Date(date + 'T00:00:00').toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatDateRange(start: string | null, end: string | null): string {
  const s = start ? formatDate(start.substring(0, 7)) : '?';
  const e = end ? formatDate(end.substring(0, 7)) : 'Present';
  return `${s} — ${e}`;
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural || singular + 's');
}

export function getActorUrl(actor: { id: number; actor_type?: string; classification?: string }): string {
  if (actor.classification === 'Political Party') return `/party/${actor.id}`;
  if (actor.actor_type === 'organization') return `/organisation/${actor.id}`;
  return `/person/${actor.id}`;
}

// UK government periods — for annotating party funding charts
// Source: well-known political history, not derived from data
export const UK_GOVERNMENTS: Array<{ start: number; end: number; party: string; pm: string; type: string }> = [
  { start: 1997, end: 2007, party: 'Labour', pm: 'Blair', type: 'majority' },
  { start: 2007, end: 2010, party: 'Labour', pm: 'Brown', type: 'majority' },
  { start: 2010, end: 2015, party: 'Conservative', pm: 'Cameron', type: 'coalition' },
  { start: 2015, end: 2016, party: 'Conservative', pm: 'Cameron', type: 'majority' },
  { start: 2016, end: 2019, party: 'Conservative', pm: 'May', type: 'majority' },
  { start: 2019, end: 2022, party: 'Conservative', pm: 'Johnson', type: 'majority' },
  { start: 2022, end: 2022, party: 'Conservative', pm: 'Truss', type: 'majority' },
  { start: 2022, end: 2024, party: 'Conservative', pm: 'Sunak', type: 'majority' },
  { start: 2024, end: 2030, party: 'Labour', pm: 'Starmer', type: 'majority' },
];

export function getGovernmentForYear(year: number): { party: string; pm: string; type: string } | null {
  for (const gov of UK_GOVERNMENTS) {
    if (year >= gov.start && year < gov.end) return gov;
  }
  return null;
}

export function isPartyInGovernment(partyName: string, year: number): boolean | null {
  const gov = getGovernmentForYear(year);
  if (!gov) return null;

  // Normalise party names for matching
  const PARTY_ALIASES: Record<string, string> = {
    'Conservative and Unionist Party': 'Conservative',
    'Conservative': 'Conservative',
    'Labour': 'Labour',
    'Labour Party': 'Labour',
    'Liberal Democrats': 'Liberal Democrat',
    'Liberal Democrat': 'Liberal Democrat',
    'Scottish National Party (SNP)': 'SNP',
    'Reform UK': 'Reform',
    'Green Party': 'Green',
    'Plaid Cymru - The Party of Wales': 'Plaid Cymru',
  };

  const normalised = PARTY_ALIASES[partyName] || partyName;
  if (normalised === gov.party) return true;

  // Coalition partners
  if (gov.type === 'coalition' && normalised === 'Liberal Democrat') return true;

  return false;
}
