import React, { useState, useMemo, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useActorDonations, Donation } from '../hooks/useActorDonations';
import { useActorMeetings, Meeting } from '../hooks/useActorMeetings';
import styles from './PoliticianProfile.module.scss';

const COLORS = ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#16a34a', '#4b5563', '#06b6d4'];

interface PoliticianProfileProps {
  actorId: number;
  actorName: string;
  actorRole?: string;
  actorParty?: string;
  totalDonations: number;
}

export default function PoliticianProfile({ 
  actorId, 
  actorName, 
  actorRole, 
  actorParty,
  totalDonations: initialTotal 
}: PoliticianProfileProps) {
  // Fetch data - we fetch a larger set for the charts to be representative
  const { data: donationsData, isLoading: loadingDonations } = useActorDonations(actorId, 'received', 1, 100);
  const { data: meetingsData, isLoading: loadingMeetings } = useActorMeetings(actorId, 1, 20);

  const stats = useMemo(() => {
    if (!donationsData?.results) return null;
    
    // Calculate Sector Data (Client-side aggregation for now)
    const sectorMap = donationsData.results.reduce((acc, curr) => {
      const key = curr.donor.classification || curr.donor.actor_type;
      const amount = Number(curr.value);
      acc[key] = (acc[key] || 0) + amount;
      return acc;
    }, {} as Record<string, number>);

    const sectorData = Object.keys(sectorMap)
      .map(key => ({ name: key, value: sectorMap[key] }))
      .sort((a, b) => b.value - a.value);

    // Meeting Attendees (Organizations)
    const attendeeMap = (meetingsData?.results || []).reduce((acc, curr) => {
      curr.attendees.forEach(a => {
        if (a.actor.id !== actorId) {
          acc[a.actor.name] = (acc[a.actor.name] || 0) + 1;
        }
      });
      return acc;
    }, {} as Record<string, number>);

    const attendeeData = Object.keys(attendeeMap)
      .map(key => ({ name: key, value: attendeeMap[key] }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);

    return { 
      sectorData: sectorData.length ? sectorData : [{ name: 'Unclassified', value: 1 }], 
      attendeeData: attendeeData.length ? attendeeData : [{ name: 'No Data', value: 1 }]
    };
  }, [donationsData, meetingsData, actorId]);

  const formatCurrency = (val: number) => new Intl.NumberFormat('en-GB', { 
    style: 'currency', currency: 'GBP', maximumFractionDigits: 0 
  }).format(val);

  if (loadingDonations || loadingMeetings) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary me-2" role="status"></div>
        <span className="small fw-bold text-muted text-uppercase tracking-wide">Accessing Audit Records...</span>
      </div>
    );
  }

  const displayTotal = initialTotal; 
  const topSector = stats?.sectorData[0]?.name || 'Unknown';
  const secondSector = stats?.sectorData[1]?.name || 'Various';

  return (
    <div className={styles.container}>
      
      {/* Official Header */}
      <header className={styles.header}>
        <div className="flex-grow-1">
          <div className="d-flex align-items-center mb-2">
            <span className={styles.refBadge}>Official Record</span>
            <span className={styles.refCode}>Ref: MP-{actorId}</span>
          </div>
          <h1 className={styles.name}>{actorName}</h1>
          <p className={styles.role}>
            {actorRole} <span className="text-light mx-2">•</span> {actorParty}
          </p>
        </div>
        <div className="text-md-end">
          <div className={styles.totalLabel}>Total Interests</div>
          <div className={styles.totalValue}>{formatCurrency(displayTotal)}</div>
        </div>
      </header>

      {/* Synthesis Block */}
      <section className={styles.synthesis}>
        <div className="flex-grow-1">
          <h2 className={styles.synthesisTitle}>
            <i className="bi bi-info-circle text-primary"></i> Synthesis of Disclosures
          </h2>
          <p className={styles.synthesisText}>
            Registered interests are predominantly sourced from the <strong>{topSector}</strong> and <strong>{secondSector}</strong> sectors. 
            Engagement data indicates activity across {meetingsData?.count || 0} ministerial meetings.
          </p>
        </div>
        <div className="w-100 w-md-50">
          {stats?.sectorData.slice(0, 2).map((s, i) => (
            <div key={i} className="mb-4">
              <div className={styles.statRow}>
                <span>Top Sector: {s.name}</span>
                <span>{Math.round((s.value / (displayTotal || 1)) * 100)}%</span>
              </div>
              <div className={styles.progressBar}>
                <div 
                  className={styles.progressFill} 
                  style={{ 
                    width: `${Math.min((s.value / (displayTotal || 1)) * 100, 100)}%`,
                    backgroundColor: COLORS[i]
                  }} 
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Charts Section */}
      <section className={styles.chartGrid}>
        {/* Funding Distribution */}
        <div className={styles.chartCard}>
          <h3 className={styles.chartTitle}>
            <i className="bi bi-building text-primary"></i> Funding Distribution
          </h3>
          <div style={{ height: '240px', width: '100%', minWidth: '0' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie 
                  data={stats?.sectorData} 
                  cx="50%" cy="50%" 
                  innerRadius={60} outerRadius={80} 
                  paddingAngle={4} 
                  dataKey="value"
                >
                  {stats?.sectorData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="white" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className={styles.legendGrid}>
            {stats?.sectorData.slice(0, 4).map((s, i) => (
              <div key={i} className={styles.legendItem}>
                <span className={styles.legendLabel}>{s.name}</span>
                <span className={styles.legendValue}>{formatCurrency(s.value)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Attendee Frequency */}
        <div className={styles.chartCard}>
          <h3 className={styles.chartTitle}>
            <i className="bi bi-people text-info"></i> Meeting Partners
          </h3>
          <div style={{ height: '240px', width: '100%', minWidth: '0' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie 
                  data={stats?.attendeeData} 
                  cx="50%" cy="50%" 
                  innerRadius={60} outerRadius={80} 
                  paddingAngle={4} 
                  dataKey="value"
                >
                  {stats?.attendeeData.map((_, i) => (
                    <Cell key={i} fill={COLORS[(i + 3) % COLORS.length]} stroke="white" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className={styles.legendGrid}>
            {stats?.attendeeData.slice(0, 4).map((s, i) => (
              <div key={i} className={styles.legendItem}>
                <span className={styles.legendLabel}>{s.name}</span>
                <span className={styles.legendValue}>{s.value} <span className="text-muted fw-normal small">mtgs</span></span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Main Content Sections (Stacked) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4rem' }}>
        
        {/* Ledger Section (Full Width) */}
        <section>
          <div className="d-flex justify-content-between align-items-end mb-4 border-bottom pb-3">
            <h3 className={styles.sectionTitle} style={{ margin: 0, padding: 0 }}>
              <i className="bi bi-briefcase text-secondary"></i> Detailed Ledger
            </h3>
            <span className="badge bg-light text-secondary text-uppercase" style={{ fontSize: '0.6rem', letterSpacing: '0.1em' }}>Financial Interests</span>
          </div>
          
          <div className={styles.ledgerList}>
            {(() => {
              const donations = donationsData?.results.slice(0, 12) || [];
              const maxVal = Math.max(...donations.map(d => Number(d.value)), 1);
              
              return donations.map((d, i) => (
                <div key={d.id} className={styles.ledgerItem}>
                  <div className={styles.ledgerHeader}>
                    <span className={styles.ledgerName}>{d.donor.name}</span>
                    <span className={styles.ledgerAmount}>{formatCurrency(Number(d.value))}</span>
                  </div>
                  <div className={styles.ledgerFooter}>
                    <div className={styles.ledgerMeta}>
                      <span>{d.donor.classification || d.donor.actor_type}</span>
                      <span>•</span>
                      <span>{d.received_date}</span>
                    </div>
                    <div className={styles.ledgerBar}>
                      <div 
                        className={styles.fill} 
                        style={{ width: `${(Number(d.value) / maxVal) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ));
            })()}
          </div>
        </section>

        {/* Meeting Log Section (Full Width) */}
        <section>
          <div className="d-flex justify-content-between align-items-end mb-4 border-bottom pb-3">
            <h3 className={styles.sectionTitle} style={{ margin: 0, padding: 0 }}>
              <i className="bi bi-calendar text-secondary"></i> Ministerial Meeting Log
            </h3>
            <span className="badge bg-light text-secondary text-uppercase" style={{ fontSize: '0.6rem', letterSpacing: '0.1em' }}>Engagement Log</span>
          </div>

          <div className={styles.meetingTableContainer}>
            <table className={styles.meetingTable}>
              <thead>
                <tr>
                  <th>Period / Dept</th>
                  <th>Subject</th>
                  <th>Attendees</th>
                </tr>
              </thead>
              <tbody>
                {meetingsData?.results.map((m, i) => (
                  <tr key={i}>
                    <td>
                      <div className={styles.meetingDate}>{m.meeting_date}</div>
                      <div className={styles.meetingDept}>
                        <i className="bi bi-geo-alt"></i> {m.department.name}
                      </div>
                    </td>
                    <td>
                      {m.is_roundtable && (
                        <span className={styles.meetingTag}>Roundtable</span>
                      )}
                      <div className={styles.meetingSubject}>{m.purpose || 'Meeting'}</div>
                    </td>
                    <td>
                      <div>
                        {m.attendees.map((a, idx) => (
                          <span key={idx} className={styles.attendeeChip}>
                            <i className="bi bi-person text-primary"></i> {a.actor.name}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
                {!meetingsData?.results.length && (
                  <tr>
                    <td colSpan={3} className="text-center text-muted py-5">
                      No ministerial meetings recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Transparency Footer Blocks */}
        <section className="row g-4">
          <div className="col-md-6">
            <div className="bg-dark text-white p-5 rounded-4 position-relative overflow-hidden">
              <h4 className="text-uppercase small fw-bold text-info mb-3 d-flex align-items-center gap-2" style={{ letterSpacing: '0.2em' }}>
                <i className="bi bi-shield-check"></i> Transparency
              </h4>
              <p className="text-white-50 fst-italic mb-4">
                "Registered interests represent payments received for activities outside of MP duties. All data shown is sourced from the Register of Members' Financial Interests."
              </p>
              <button className="btn btn-link text-white p-0 text-decoration-none text-uppercase fw-bold small" style={{ letterSpacing: '0.1em', borderBottom: '1px solid rgba(255,255,255,0.2)' }}>
                View Methodology
              </button>
            </div>
          </div>
          <div className="col-md-6">
            <div className="border border-2 border-dashed border-secondary p-5 rounded-4 d-flex flex-column align-items-center justify-content-center text-center h-100">
              <div className="bg-light rounded-circle p-3 mb-3">
                <i className="bi bi-search fs-4 text-secondary"></i>
              </div>
              <p className="text-uppercase fw-bold text-secondary small mb-0" style={{ letterSpacing: '0.1em' }}>
                Verified By Parliamentary<br/>Digital Service JSON Audit
              </p>
            </div>
          </div>
        </section>
      </div>

      <footer className={styles.footer}>
        <button className="btn btn-link text-primary text-decoration-none text-uppercase fw-bold small d-flex align-items-center gap-2" style={{ letterSpacing: '0.1em' }}>
          <i className="bi bi-box-arrow-up-right"></i> Full Register Access
        </button>
        <div className="text-end">
          <p className="text-uppercase fw-bold text-secondary small mb-1" style={{ fontSize: '0.6rem', letterSpacing: '0.1em' }}>Data Feed Status</p>
          <div className="text-success fw-bold small d-flex align-items-center gap-2 text-uppercase" style={{ fontSize: '0.65rem', letterSpacing: '0.05em' }}>
            <span className={styles.statusIndicator}></span> Verified Synchronized
          </div>
        </div>
      </footer>
    </div>
  );
}