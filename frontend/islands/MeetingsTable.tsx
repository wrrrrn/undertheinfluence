import React, { useState } from 'react';
import { useActorMeetings, Meeting } from '../hooks/useActorMeetings';
import { SimpleTable, Column } from '../components/SimpleTable';

interface MeetingsTableProps {
  actorId: number;
}

export default function MeetingsTable({ actorId }: MeetingsTableProps) {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useActorMeetings(actorId, page);

  const columns: Column<Meeting>[] = [
    {
      header: 'Date',
      accessor: (m) => m.meeting_date || <span className="text-muted">-</span>,
      className: 'text-nowrap'
    },
    {
      header: 'Department',
      accessor: (m) => m.department?.name || <span className="text-muted">Unknown</span>
    },
    {
      header: 'Minister',
      accessor: (m) => (
        <a href={`/person/${m.minister.id}/`} className="fw-medium text-decoration-none">
          {m.minister.name}
        </a>
      )
    },
    {
      header: 'Purpose',
      accessor: (m) => m.purpose
    },
    {
      header: 'Attendees',
      accessor: (m) => {
        if (m.is_roundtable) {
          return (
            <div>
              <span className="badge bg-secondary mb-1">Roundtable</span>
              <div className="small text-muted text-truncate" style={{ maxWidth: '200px' }} title={m.organisation_met_raw}>
                {m.attendees.map(a => a.actor.name).join(', ')}
              </div>
            </div>
          );
        }
        return m.organisation_met_raw;
      }
    }
  ];

  return (
    <SimpleTable
      data={data?.results || []}
      columns={columns}
      isLoading={isLoading}
      totalCount={data?.count || 0}
      currentPage={page}
      onPageChange={setPage}
      emptyMessage="No ministerial meetings found."
    />
  );
}
