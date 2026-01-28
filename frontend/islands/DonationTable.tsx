import React, { useState } from 'react';
import { useActorDonations, Donation } from '../hooks/useActorDonations';
import { SimpleTable, Column } from '../components/SimpleTable';

interface DonationTableProps {
  actorId: number;
  direction: 'received' | 'made';
}

export default function DonationTable({ actorId, direction }: DonationTableProps) {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useActorDonations(actorId, direction, page);

  const columns: Column<Donation>[] = [
    {
      header: direction === 'received' ? 'Donor' : 'Recipient',
      accessor: (d) => {
        const actor = direction === 'received' ? d.donor : d.recipient;
        if (!actor) return <span className="text-muted">Unknown</span>;
        
        const url = actor.actor_type === 'person' 
          ? `/person/${actor.id}/` 
          : `/organization/${actor.id}/`;
          
        return <a href={url} className="fw-medium text-decoration-none">{actor.name}</a>;
      }
    },
    {
      header: 'Amount',
      accessor: (d) => <span className="tabular-nums fw-bold">£{Number(d.value).toLocaleString()}</span>,
      className: 'text-end'
    },
    {
      header: 'Date',
      accessor: (d) => d.received_date || d.accepted_date || <span className="text-muted">-</span>
    },
    {
      header: 'Type',
      accessor: (d) => (
        <span className="badge bg-light text-dark border">
          {d.donation_type}
        </span>
      )
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
      emptyMessage="No donations found."
    />
  );
}
