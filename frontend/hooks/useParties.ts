import { useQuery } from '@tanstack/react-query';

interface Party {
  id: number;
  name: string;
  is_governing: boolean;
  mp_count: number;
  lord_count: number;
}

export function useParties() {
  return useQuery<Party[]>({
    queryKey: ['parties'],
    queryFn: async () => {
      const response = await fetch('/api/v2/parties/');
      if (!response.ok) {
        throw new Error('Failed to fetch parties');
      }
      return response.json();
    },
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}
