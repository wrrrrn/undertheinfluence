import { useQuery } from '@tanstack/react-query';
import { useFilterStore } from '../store/filterStore';
import { Politician } from '../components/PoliticianCard';

interface PoliticiansResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Politician[];
}

export function usePoliticians() {
  const { 
    query, roleType, partyId, govtStatus, page, limit 
  } = useFilterStore();

  const queryParams = new URLSearchParams();
  
  if (query) queryParams.set('search', query);
  if (roleType) queryParams.set('role_type', roleType);
  if (partyId) queryParams.set('party', String(partyId));
  if (govtStatus) queryParams.set('govt_status', govtStatus);
  
  queryParams.set('page', String(page));
  queryParams.set('limit', String(limit));

  return useQuery<PoliticiansResponse>({
    queryKey: ['politicians', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/politicians/?${queryParams}`);
      if (!response.ok) {
        throw new Error('Failed to fetch politicians');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
