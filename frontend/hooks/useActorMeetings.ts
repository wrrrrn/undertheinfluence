import { useQuery } from '@tanstack/react-query';

export interface Meeting {
  id: number;
  minister: {
    id: number;
    name: string;
    actor_type: string;
  };
  department: {
    id: number;
    name: string;
    actor_type: string;
  };
  meeting_date: string;
  purpose: string;
  is_roundtable: boolean;
  organisation_met_raw: string;
  attendees: {
    id: number;
    actor: {
      id: number;
      name: string;
    };
  }[];
}

interface MeetingResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Meeting[];
}

export function useActorMeetings(
  actorId: number, 
  page: number = 1,
  limit: number = 20
) {
  const offset = (page - 1) * limit;

  return useQuery<MeetingResponse>({
    queryKey: ['actor-meetings', actorId, page, limit],
    queryFn: async () => {
      const response = await fetch(`/api/v2/actors/${actorId}/meetings/?limit=${limit}&offset=${offset}`);
      if (!response.ok) throw new Error('Failed to fetch meetings');
      return response.json();
    },
    staleTime: 5 * 60 * 1000,
  });
}
