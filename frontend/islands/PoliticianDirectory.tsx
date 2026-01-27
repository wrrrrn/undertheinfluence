import React from 'react';
import { PoliticianFilters } from '../components/PoliticianFilters';
import { PoliticianList } from '../components/PoliticianList';

// Main directory island for the /politicians/ page
export default function PoliticianDirectory() {
  return (
    <div className="row g-4">
      <div className="col-lg-3">
        <PoliticianFilters />
      </div>
      <div className="col-lg-9">
        <PoliticianList />
      </div>
    </div>
  );
}
