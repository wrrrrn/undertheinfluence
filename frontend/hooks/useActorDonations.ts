import { useQuery } from '@tanstack/react-query';

export interface Donation {
  id: number;
  donor: {
    id: number;
    name: string;
    actor_type: string;
    classification?: string;
  };
  recipient: {
    id: number;
    name: string;
    actor_type: string;
    classification?: string;
  };
  value: string; // Decimal string
  received_date?: string;
  accepted_date?: string;
  donation_type: string;
  nature_of_donation?: string;
  donor_key_people?: {
    id: number;
    name: string;
    role: string;
  }[];
}

interface DonationResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Donation[];
}

export function useActorDonations(
  actorId: number, 
  direction: 'received' | 'made',
  page: number = 1,
  limit: number = 20
) {
  const endpoint = direction === 'received' 
    ? `/api/v2/actors/${actorId}/donations-received/`
    : `/api/v2/actors/${actorId}/donations-made/`;

  const offset = (page - 1) * limit;

  return useQuery<DonationResponse>({
    queryKey: ['actor-donations', actorId, direction, page, limit],
    queryFn: async () => {
      const response = await fetch(`${endpoint}?limit=${limit}&offset=${offset}`);
      if (!response.ok) throw new Error('Failed to fetch donations');
      return response.json();
    },
    staleTime: 5 * 60 * 1000,
  });
}
