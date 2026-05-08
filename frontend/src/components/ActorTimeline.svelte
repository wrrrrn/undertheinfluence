<script lang="ts">
  import { formatCurrency, formatDate, formatDateRange, PUBLIC_API_URL } from '../lib/utils';

  interface Props {
    actor: any;
    donations: any;
    donationsMade: any;
    memberships: any;
    meetings: any;
    consultancies: any;
    yearlyTotals?: any[] | null;
    actorId?: number;
  }

  let {
    actor,
    donations,
    donationsMade,
    memberships,
    meetings,
    consultancies,
    yearlyTotals = null,
    actorId,
  }: Props = $props();

  const COLLAPSE_THRESHOLD = 5;
  const isOrg = actor.actor_type === 'organization';
  const isLazyMode = yearlyTotals && yearlyTotals.length > 0 && donations.results.length === 0;
  const CLIENT_API_URL = PUBLIC_API_URL;

  type TimelineEvent = {
    type: 'role' | 'donation_received' | 'donation_made' | 'meeting' | 'consultancy';
    date: string;
    data: any;
    activeRole: string | null;
  };

  type YearGroup = {
    year: string;
    roles: TimelineEvent[];
    donations: TimelineEvent[];
    donationsMade: TimelineEvent[];
    meetings: TimelineEvent[];
    consultancies: TimelineEvent[];
    donationTotal: number;
    topDonors: Array<{ name: string; id: number; total: number; count: number }>;
    topMeetingOrgs: Array<{ name: string; id: number | null; count: number }>;
    topCoAttendees: Array<{ name: string; id: number | null; count: number }>;
    topClients: Array<{ name: string; id: number | null; count: number }>;
  };

  function getDonationDate(d: any): string | null {
    return d.accepted_date || d.reported_date || d.received_date || null;
  }

  function getActiveRole(date: string): string | null {
    if (!date || !memberships.results) return null;
    const active = memberships.results.filter((m: any) => {
      if (!m.start_date) return false;
      const start = m.start_date.substring(0, 10);
      const end = m.end_date ? m.end_date.substring(0, 10) : '9999-12-31';
      return start <= date && date <= end;
    });
    const ministerial = active.find((m: any) =>
      m.role && !m.role.startsWith('Member of Parliament') &&
      !m.role.startsWith('Member of the ') &&
      !m.role.includes('Leader of')
    );
    if (ministerial) return ministerial.role;
    const leader = active.find((m: any) => m.role?.includes('Leader of'));
    if (leader) return leader.role;
    const mp = active.find((m: any) => m.role?.startsWith('Member of Parliament'));
    if (mp) return mp.role;
    return active.length > 0 ? active[0].role : null;
  }

  function buildYearGroups(): YearGroup[] {
    const groups = new Map<string, YearGroup>();

    function getGroup(year: string): YearGroup {
      if (!groups.has(year)) {
        groups.set(year, {
          year,
          roles: [],
          donations: [],
          donationsMade: [],
          meetings: [],
          consultancies: [],
          donationTotal: 0,
          topDonors: [],
          topMeetingOrgs: [],
          topCoAttendees: [],
          topClients: [],
        });
      }
      return groups.get(year)!;
    }

    // Roles — for orgs, memberships are the org's members (directors/PSCs), shown in header not timeline
    if (!isOrg) {
      // Deduplicate by normalised org name + role to collapse duplicate org records
      const seenRoles = new Set<string>();
      for (const m of memberships.results) {
        if (!m.start_date) continue;
        const orgName = (m.organization?.name || 'none').toLowerCase().replace(/\s+(limited|ltd|plc)\.?$/i, '').trim();
        const dedupeKey = `${orgName}-${(m.role || 'none').toLowerCase()}`;
        if (seenRoles.has(dedupeKey)) continue;
        seenRoles.add(dedupeKey);
        const year = m.start_date.substring(0, 4);
        getGroup(year).roles.push({ type: 'role', date: m.start_date, data: m, activeRole: null });
      }
    }

    // Donations received
    const donorTotals = new Map<string, { name: string; id: number; total: number; count: number }>();
    for (const d of donations.results) {
      const date = getDonationDate(d);
      if (!date) continue;
      const year = date.substring(0, 4);
      const g = getGroup(year);
      g.donations.push({ type: 'donation_received', date, data: d, activeRole: getActiveRole(date) });
      g.donationTotal += parseFloat(d.value) || 0;

      // Track top donors per year
      const key = `${year}-${d.donor.id}`;
      const existing = donorTotals.get(key);
      if (existing) {
        existing.total += parseFloat(d.value) || 0;
        existing.count++;
      } else {
        donorTotals.set(key, { name: d.donor.name, id: d.donor.id, total: parseFloat(d.value) || 0, count: 1 });
      }
    }

    // Donations made
    for (const d of donationsMade.results) {
      const date = getDonationDate(d);
      if (!date) continue;
      const year = date.substring(0, 4);
      getGroup(year).donationsMade.push({ type: 'donation_made', date, data: d, activeRole: getActiveRole(date) });
    }

    // Meetings — track primary contacts and co-attendees separately
    // isOrg is defined at component scope (line 23)
    const meetingOrgCounts = new Map<string, { name: string; id: number | null; count: number }>();
    const coAttendeeCounts = new Map<string, { name: string; id: number | null; count: number }>();

    for (const m of meetings.results) {
      if (!m.meeting_date) continue;
      const year = m.meeting_date.substring(0, 4);
      getGroup(year).meetings.push({ type: 'meeting', date: m.meeting_date, data: m, activeRole: getActiveRole(m.meeting_date) });

      if (isOrg) {
        // For org pages: primary = ministers met, secondary = co-attendees
        if (m.minister && m.minister.id !== actor.id) {
          const key = `${year}-minister-${m.minister.id}`;
          const existing = meetingOrgCounts.get(key);
          if (existing) {
            existing.count++;
          } else {
            meetingOrgCounts.set(key, { name: m.minister.name, id: m.minister.id, count: 1 });
          }
        }
        // Track co-attendees for "Frequently with" line
        if (m.attendees) {
          for (const att of m.attendees) {
            if (att.actor?.id === actor.id) continue;
            // Also skip name-duplicates of self (unresolved duplicate org records)
            if (att.actor?.name?.toLowerCase() === actor.name?.toLowerCase()) continue;
            const attId = att.actor?.id || null;
            const attName = att.actor?.name || att.actor_name_raw || 'Unknown';
            const key = `${year}-att-${attId || `raw-${attName}`}`;
            const existing = coAttendeeCounts.get(key);
            if (existing) {
              existing.count++;
            } else {
              coAttendeeCounts.set(key, { name: attName, id: attId, count: 1 });
            }
          }
        }
      } else {
        // For politician pages: primary = attendees/orgs met
        if (m.attendees && m.attendees.length > 0) {
          for (const att of m.attendees) {
            if (att.actor?.id === actor.id) continue;
            const attId = att.actor?.id || null;
            const attName = att.actor?.name || att.actor_name_raw || 'Unknown';
            const orgKey = `${year}-${attId || `raw-${attName}`}`;
            const existing = meetingOrgCounts.get(orgKey);
            if (existing) {
              existing.count++;
            } else {
              meetingOrgCounts.set(orgKey, { name: attName, id: attId, count: 1 });
            }
          }
        } else if (m.organisation_met_raw) {
          const orgKey = `${year}-raw-${m.organisation_met_raw}`;
          const existing = meetingOrgCounts.get(orgKey);
          if (existing) {
            existing.count++;
          } else {
            meetingOrgCounts.set(orgKey, { name: m.organisation_met_raw, id: null, count: 1 });
          }
        }
      }
    }

    // Consultancies — track top clients for collapse summary
    const clientCounts = new Map<string, { name: string; id: number | null; count: number }>();
    for (const c of consultancies.results) {
      if (!c.start_date) continue;
      const year = c.start_date.substring(0, 4);
      getGroup(year).consultancies.push({ type: 'consultancy', date: c.start_date, data: c, activeRole: getActiveRole(c.start_date) });

      // Track counterparty for collapse summary
      const isAgencyHere = c.agency?.id === actor.id;
      const counterparty = isAgencyHere ? c.client : c.agency;
      if (counterparty) {
        const key = `${year}-${counterparty.id || counterparty.name}`;
        const existing = clientCounts.get(key);
        if (existing) {
          existing.count++;
        } else {
          clientCounts.set(key, { name: counterparty.name, id: counterparty.id || null, count: 1 });
        }
      }
    }

    // Compute top donors and meeting orgs per year
    for (const [key, donor] of donorTotals) {
      const year = key.split('-')[0];
      const g = groups.get(year);
      if (g) g.topDonors.push(donor);
    }
    for (const [key, org] of meetingOrgCounts) {
      const year = key.split('-')[0];
      const g = groups.get(year);
      if (g) g.topMeetingOrgs.push(org);
    }
    for (const [key, att] of coAttendeeCounts) {
      const year = key.split('-')[0];
      const g = groups.get(year);
      if (g) g.topCoAttendees.push(att);
    }
    for (const [key, client] of clientCounts) {
      const year = key.split('-')[0];
      const g = groups.get(year);
      if (g) g.topClients.push(client);
    }

    // Sort top donors/orgs
    for (const g of groups.values()) {
      g.topDonors.sort((a, b) => b.total - a.total);
      g.topMeetingOrgs.sort((a, b) => b.count - a.count);
      g.topCoAttendees.sort((a, b) => b.count - a.count);
      g.topClients.sort((a, b) => b.count - a.count);
      g.donations.sort((a, b) => b.date.localeCompare(a.date));
      g.meetings.sort((a, b) => b.date.localeCompare(a.date));
    }

    // In lazy mode, ensure all years from yearlyTotals have groups (even if no pre-loaded donations)
    if (isLazyMode && yearlyTotals) {
      for (const yt of yearlyTotals) {
        if (!groups.has(yt.year)) {
          const g = getGroup(yt.year);
          // Populate top donors from funding summary
          if (yt.top_donors) {
            g.topDonors = yt.top_donors.map((d: any) => ({
              name: d.name, id: d.id, total: parseFloat(d.total), count: d.count
            }));
          }
          g.donationTotal = parseFloat(yt.total) || 0;
        }
      }
    }

    return Array.from(groups.values()).sort((a, b) => b.year.localeCompare(a.year));
  }

  const yearGroups = buildYearGroups();
  const totalEvents = donations.count + donationsMade.count + meetings.count + consultancies.count;

  // GN9: per-type max across years, used to scale the hatched proportional bar on collapsed summaries
  const maxDonationTotal = Math.max(1, ...yearGroups.map(g => g.donationTotal));
  const maxMeetingCount = Math.max(1, ...yearGroups.map(g => g.meetings.length));
  const maxConsultancyCount = Math.max(1, ...yearGroups.map(g => g.consultancies.length));

  // Track which year sections are expanded
  let expandedDonations = $state<Set<string>>(new Set());
  let expandedMeetings = $state<Set<string>>(new Set());
  let expandedConsultancies = $state<Set<string>>(new Set());

  // Lazy loading state for party pages
  let lazyLoadedDonations = $state<Map<string, any[]>>(new Map());
  let lazyLoadingYears = $state<Set<string>>(new Set());
  let lazyLoadedCounts = $state<Map<string, number>>(new Map());

  async function fetchYearDonations(year: string) {
    if (!actorId || lazyLoadedDonations.has(year)) return;
    const next = new Set(lazyLoadingYears);
    next.add(year);
    lazyLoadingYears = next;

    try {
      const res = await fetch(
        `${CLIENT_API_URL}/actors/${actorId}/donations/?role=recipient&received_after=${year}-01-01&received_before=${year}-12-31&limit=500`
      );
      if (res.ok) {
        const data = await res.json();
        const newMap = new Map(lazyLoadedDonations);
        newMap.set(year, data.results);
        lazyLoadedDonations = newMap;
        const newCounts = new Map(lazyLoadedCounts);
        newCounts.set(year, data.count);
        lazyLoadedCounts = newCounts;
      }
    } finally {
      const next = new Set(lazyLoadingYears);
      next.delete(year);
      lazyLoadingYears = next;
    }
  }

  function toggleDonations(year: string) {
    if (isLazyMode && !lazyLoadedDonations.has(year)) {
      // Fetch data first, then expand
      fetchYearDonations(year).then(() => {
        const next = new Set(expandedDonations);
        next.add(year);
        expandedDonations = next;
      });
      return;
    }
    const next = new Set(expandedDonations);
    if (next.has(year)) next.delete(year); else next.add(year);
    expandedDonations = next;
  }

  function toggleMeetings(year: string) {
    const next = new Set(expandedMeetings);
    if (next.has(year)) next.delete(year); else next.add(year);
    expandedMeetings = next;
  }

  function toggleConsultancies(year: string) {
    const next = new Set(expandedConsultancies);
    if (next.has(year)) next.delete(year); else next.add(year);
    expandedConsultancies = next;
  }
</script>

{#if yearGroups.length === 0}
  <p class="text-ink-muted italic">No recorded activity for this actor.</p>
{:else}
  <!-- GN9: shared hatched pattern defs, document-scoped so every year-bar SVG can reference them -->
  <svg width="0" height="0" class="absolute" aria-hidden="true" style="position:absolute">
    <defs>
      <pattern id="hatch-donation-year" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="5" stroke="#5B7355" stroke-width="1.2" opacity="0.65"/>
      </pattern>
      <pattern id="hatch-meeting-year" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
        <line x1="0" y1="0" x2="0" y2="5" stroke="#4A7BA7" stroke-width="1.2" opacity="0.6"/>
      </pattern>
      <pattern id="hatch-consultancy-year" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="5" stroke="#DAA520" stroke-width="1.2" opacity="0.7"/>
      </pattern>
    </defs>
  </svg>
  <div class="timeline">
    {#each yearGroups as group}
      {@const hasDonations = group.donations.length > 0 || group.topDonors.length > 0}
      {@const hasDonationsMade = group.donationsMade.length > 0}
      {@const hasMeetings = group.meetings.length > 0}
      {@const hasRoles = group.roles.length > 0}
      {@const hasConsultancies = group.consultancies.length > 0}
      <!-- Year marker -->
      <h2 class="year-marker">
        <span class="year-glyphs" aria-hidden="true">
          {#if hasDonations || hasDonationsMade}<span class="glyph" style="color:#5B7355">●</span>{/if}
          {#if hasMeetings}<span class="glyph" style="color:#7B9E87">▲</span>{/if}
          {#if hasRoles}<span class="glyph" style="color:#4A7BA7">◆</span>{/if}
          {#if hasConsultancies}<span class="glyph" style="color:#DAA520">◉</span>{/if}
        </span>
        <span class="year-label">{group.year}</span>
        <span class="plate-rule" aria-hidden="true"></span>
      </h2>

      <!-- Roles always shown individually -->
      {#each group.roles as event}
        <div class="timeline-row role-row">
          <div class="timeline-date">
            <span class="date-text">{formatDateRange(event.data.start_date, event.data.end_date)}</span>
          </div>
          <div class="timeline-content role-content">
            <span class="font-display font-semibold">{event.data.role}</span>
            {#if event.data.organization?.id}
              <a href="/person/{event.data.organization.id}" class="meta-text ml-2 hover:text-accent transition-colors">{event.data.organization.name}</a>
            {:else if event.data.organization}
              <span class="meta-text ml-2">{event.data.organization.name}</span>
            {/if}
          </div>
        </div>
      {/each}

      <!-- Donations: lazy mode (party pages) or pre-loaded -->
      {#if isLazyMode && group.donations.length === 0 && group.topDonors.length > 0}
        <!-- Lazy mode: show summary from funding data, fetch on expand -->
        {@const yearData = yearlyTotals?.find((yt: any) => yt.year === group.year)}
        {@const yearDonationCount = yearData?.count || 0}
        {@const yearUniqueCount = yearData?.unique_donors || group.topDonors.length}
        {#if !expandedDonations.has(group.year)}
          <!-- Collapsed: show funding summary data -->
          <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleDonations(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleDonations(group.year); } }}>
            <div class="timeline-date">
              <span class="date-text">{yearDonationCount} donations</span>
            </div>
            <div class="timeline-content donation-border summary-content">
              <div class="flex items-baseline justify-between gap-4 mb-2">
                <div>
                  <span class="font-display font-bold text-lg">{formatCurrency(group.donationTotal)}</span>
                  <span class="meta-text ml-2">from {yearUniqueCount} donors</span>
                </div>
                <span class="expand-label">{lazyLoadingYears.has(group.year) ? 'Loading...' : `Show all ${yearDonationCount} ▸`}</span>
              </div>
              <svg class="year-bar" aria-hidden="true">
                <rect x="0" y="0" width="100%" height="100%" fill="#1a1a1a" fill-opacity="0.03"/>
                <rect x="0" y="0" width="{(group.donationTotal / maxDonationTotal) * 100}%" height="100%" fill="url(#hatch-donation-year)"/>
              </svg>
              <div class="space-y-1 mt-2">
                {#each group.topDonors.slice(0, 5) as donor}
                  <div class="flex items-baseline justify-between gap-2">
                    <a href="/person/{donor.id}" class="text-[11px] font-display font-semibold truncate hover:text-accent transition-colors" title={donor.name}>
                      {donor.name}
                    </a>
                    <div class="flex items-baseline gap-2 shrink-0">
                      <span class="text-[10px] text-ink-muted">{donor.count}×</span>
                      <span class="text-[11px] font-display font-bold tabular">{formatCurrency(donor.total)}</span>
                    </div>
                  </div>
                {/each}
                {#if yearUniqueCount > 5}
                  <p class="text-[10px] text-ink-muted">+ {yearUniqueCount - 5} more donors</p>
                {/if}
              </div>
            </div>
          </div>
        {:else}
          <!-- Expanded: show fetched donations -->
          <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleDonations(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleDonations(group.year); } }}>
            <div class="timeline-date">
              <span class="date-text">{lazyLoadedCounts.get(group.year) || yearDonationCount} donations</span>
            </div>
            <div class="timeline-content donation-border summary-content">
              <div class="flex items-baseline justify-between gap-4">
                <div>
                  <span class="font-display font-bold text-lg">{formatCurrency(group.donationTotal)}</span>
                  <span class="meta-text ml-2">from {yearUniqueCount} donors</span>
                </div>
                <span class="expand-label">Collapse ▾</span>
              </div>
            </div>
          </div>
          {#each lazyLoadedDonations.get(group.year) || [] as donation}
            <div class="timeline-row">
              <div class="timeline-date">
                <span class="date-text tabular">{formatDate(donation.accepted_date || donation.received_date || donation.reported_date)}</span>
              </div>
              <div class="timeline-content donation-border">
                <div class="flex items-baseline justify-between gap-4">
                  <div class="min-w-0">
                    <a href="/person/{donation.donor.id}" class="font-display font-semibold hover:text-accent transition-colors" title={donation.donor.name}>
                      {donation.donor.name}
                    </a>
                    {#if donation.donation_type}
                      <span class="type-badge">{donation.donation_type}</span>
                    {/if}
                  </div>
                  <span class="font-display font-bold text-lg tabular shrink-0">
                    {formatCurrency(donation.value)}
                  </span>
                </div>
                {#if donation.purpose_of_visit}
                  <p class="text-[11px] text-ink-light mt-1">{donation.purpose_of_visit}</p>
                {/if}
                {#if donation.donor_key_people && donation.donor_key_people.length > 0}
                  <div class="text-[9px] text-ink-muted mt-1 pl-2 border-l-2 border-accent/20">
                    {donation.donor_key_people.map((p: any) => `${p.name} (${p.role})`).join(' · ')}
                  </div>
                {/if}
              </div>
            </div>
          {/each}
        {/if}

      {:else if group.donations.length > COLLAPSE_THRESHOLD && !expandedDonations.has(group.year)}
        <!-- Pre-loaded: collapsed donation summary -->
        <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleDonations(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleDonations(group.year); } }}>
          <div class="timeline-date">
            <span class="date-text">{group.donations.length} donations</span>
          </div>
          <div class="timeline-content donation-border summary-content">
            <div class="flex items-baseline justify-between gap-4 mb-2">
              <div>
                <span class="font-display font-bold text-lg">{formatCurrency(group.donationTotal)}</span>
                <span class="meta-text ml-2">from {group.topDonors.length} donors</span>
              </div>
              <span class="expand-label">Show all {group.donations.length} ▸</span>
            </div>
            <svg class="year-bar" aria-hidden="true">
              <rect x="0" y="0" width="100%" height="100%" fill="#1a1a1a" fill-opacity="0.03"/>
              <rect x="0" y="0" width="{(group.donationTotal / maxDonationTotal) * 100}%" height="100%" fill="url(#hatch-donation-year)"/>
            </svg>
            <div class="space-y-1 mt-2">
              {#each group.topDonors.slice(0, 5) as donor}
                <div class="flex items-baseline justify-between gap-2">
                  <a href="/person/{donor.id}" class="text-[11px] font-display font-semibold truncate hover:text-accent transition-colors" title={donor.name}>
                    {donor.name}
                  </a>
                  <div class="flex items-baseline gap-2 shrink-0">
                    <span class="text-[10px] text-ink-muted">{donor.count}×</span>
                    <span class="text-[11px] font-display font-bold tabular">{formatCurrency(donor.total)}</span>
                  </div>
                </div>
              {/each}
              {#if group.topDonors.length > 5}
                <p class="text-[10px] text-ink-muted">+ {group.topDonors.length - 5} more donors</p>
              {/if}
            </div>
          </div>
        </div>

      {:else if group.donations.length > 0}
        <!-- Pre-loaded: individual donations (or expanded) -->
        {#if group.donations.length > COLLAPSE_THRESHOLD}
          <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleDonations(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleDonations(group.year); } }}>
            <div class="timeline-date">
              <span class="date-text">{group.donations.length} donations</span>
            </div>
            <div class="timeline-content donation-border summary-content">
              <div class="flex items-baseline justify-between gap-4">
                <div>
                  <span class="font-display font-bold text-lg">{formatCurrency(group.donationTotal)}</span>
                  <span class="meta-text ml-2">from {group.topDonors.length} donors</span>
                </div>
                <span class="expand-label">Collapse ▾</span>
              </div>
            </div>
          </div>
        {/if}
        {#each group.donations as event}
          <div class="timeline-row">
            <div class="timeline-date">
              <span class="date-text tabular">{formatDate(event.date)}</span>
              {#if event.activeRole}
                <span class="role-context" title={event.activeRole}>
                  as {event.activeRole.length > 35 ? event.activeRole.substring(0, 33) + '...' : event.activeRole}
                </span>
              {/if}
            </div>
            <div class="timeline-content donation-border">
              <div class="flex items-baseline justify-between gap-4">
                <div class="min-w-0">
                  <a href="/person/{event.data.donor.id}" class="font-display font-semibold hover:text-accent transition-colors" title={event.data.donor.name}>
                    {event.data.donor.name}
                  </a>
                  {#if event.data.donation_type}
                    <span class="type-badge">{event.data.donation_type}</span>
                  {/if}
                </div>
                <span class="font-display font-bold text-lg tabular shrink-0">
                  {formatCurrency(event.data.value)}
                </span>
              </div>
              {#if event.data.purpose_of_visit}
                <p class="text-[11px] text-ink-light mt-1">{event.data.purpose_of_visit}</p>
              {/if}
              {#if event.data.donor_key_people && event.data.donor_key_people.length > 0}
                <div class="text-[9px] text-ink-muted mt-1 pl-2 border-l-2 border-accent/20">
                  {event.data.donor_key_people.map((p: any) => `${p.name} (${p.role})`).join(' · ')}
                </div>
              {/if}
            </div>
          </div>
        {/each}
      {/if}

      <!-- Donations made (always individual — typically low volume) -->
      {#each group.donationsMade as event}
        <div class="timeline-row">
          <div class="timeline-date">
            <span class="date-text tabular">{formatDate(event.date)}</span>
          </div>
          <div class="timeline-content donated-border">
            <div class="flex items-baseline justify-between gap-4">
              <div class="min-w-0">
                <span class="meta-text uppercase tracking-wider mr-1">Donated to</span>
                <a href="/person/{event.data.recipient.id}" class="font-display font-semibold hover:text-accent transition-colors">
                  {event.data.recipient.name}
                </a>
                {#if event.data.recipient_party}
                  <span class="text-xs text-ink-muted ml-1.5">· {event.data.recipient_party.name}</span>
                {/if}
              </div>
              <span class="font-display font-bold text-lg tabular shrink-0">
                {formatCurrency(event.data.value)}
              </span>
            </div>
            {#if event.data.recipient_role_at_date}
              <div class="text-[11px] text-ink-muted mt-0.5">{event.data.recipient_role_at_date}</div>
            {/if}
          </div>
        </div>
      {/each}

      <!-- Meetings: summary or individual -->
      {#if group.meetings.length > COLLAPSE_THRESHOLD && !expandedMeetings.has(group.year)}
        <!-- Collapsed meeting summary -->
        <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleMeetings(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleMeetings(group.year); } }}>
          <div class="timeline-date">
            <span class="date-text">{group.meetings.length} meetings</span>
          </div>
          <div class="timeline-content meeting-border summary-content">
            <div class="flex items-baseline justify-between gap-4 mb-2">
              <div>
                <span class="font-display font-bold">{group.meetings.length} meetings</span>
                <span class="meta-text ml-2">with {group.topMeetingOrgs.length} {isOrg ? (group.topMeetingOrgs.length === 1 ? 'minister' : 'ministers') : (group.topMeetingOrgs.length === 1 ? 'organisation' : 'organisations')}</span>
              </div>
              <span class="expand-label">Show all {group.meetings.length} ▸</span>
            </div>
            <svg class="year-bar" aria-hidden="true">
              <rect x="0" y="0" width="100%" height="100%" fill="#1a1a1a" fill-opacity="0.03"/>
              <rect x="0" y="0" width="{(group.meetings.length / maxMeetingCount) * 100}%" height="100%" fill="url(#hatch-meeting-year)"/>
            </svg>
            <!-- Top meeting contacts -->
            <div class="space-y-1 mt-2">
              {#each group.topMeetingOrgs.slice(0, 5) as org}
                <div class="flex items-baseline justify-between gap-2 min-w-0">
                  {#if org.id}
                    <a href="/person/{org.id}" class="text-[11px] truncate min-w-0 hover:text-accent transition-colors" title={org.name}>{org.name}</a>
                  {:else}
                    <span class="text-[11px] truncate min-w-0" title={org.name}>{org.name}</span>
                  {/if}
                  <span class="text-[10px] text-ink-muted shrink-0 tabular">{org.count} {org.count === 1 ? 'meeting' : 'meetings'}</span>
                </div>
              {/each}
              {#if group.topMeetingOrgs.length > 5}
                <p class="text-[10px] text-ink-muted">+ {group.topMeetingOrgs.length - 5} more {isOrg ? 'ministers' : 'organisations'}</p>
              {/if}
            </div>
            <!-- Co-attendees (org pages only) -->
            {#if isOrg && group.topCoAttendees.length > 0}
              <div class="mt-2 pt-2 border-t border-ink/5">
                <span class="text-[10px] text-ink-muted">Frequently with: </span>
                {#each group.topCoAttendees.slice(0, 4) as att, i}
                  {#if att.id}
                    <a href="/person/{att.id}" class="text-[10px] text-ink-muted hover:text-accent transition-colors">{att.name}</a>{i < Math.min(group.topCoAttendees.length, 4) - 1 ? ', ' : ''}
                  {:else}
                    <span class="text-[10px] text-ink-muted">{att.name}</span>{i < Math.min(group.topCoAttendees.length, 4) - 1 ? ', ' : ''}
                  {/if}
                {/each}
              </div>
            {/if}
          </div>
        </div>

      {:else if group.meetings.length > 0}
        <!-- Individual meetings (or expanded) -->
        {#if group.meetings.length > COLLAPSE_THRESHOLD}
          <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleMeetings(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleMeetings(group.year); } }}>
            <div class="timeline-date">
              <span class="date-text">{group.meetings.length} meetings</span>
            </div>
            <div class="timeline-content meeting-border summary-content">
              <div class="flex items-baseline justify-between gap-4">
                <div>
                  <span class="font-display font-bold">{group.meetings.length} meetings</span>
                  <span class="meta-text ml-2">with {group.topMeetingOrgs.length} {isOrg ? (group.topMeetingOrgs.length === 1 ? 'minister' : 'ministers') : (group.topMeetingOrgs.length === 1 ? 'organisation' : 'organisations')}</span>
                </div>
                <span class="expand-label">Collapse ▾</span>
              </div>
            </div>
          </div>
        {/if}
        {#each group.meetings as event}
          <div class="timeline-row">
            <div class="timeline-date">
              <span class="date-text tabular">{formatDate(event.date)}</span>
              {#if event.activeRole}
                <span class="role-context" title={event.activeRole}>
                  as {event.activeRole.length > 35 ? event.activeRole.substring(0, 33) + '...' : event.activeRole}
                </span>
              {/if}
            </div>
            <div class="timeline-content meeting-border">
              {#if event.data.purpose}
                <p class="text-sm text-ink leading-snug font-medium">{event.data.purpose}</p>
              {/if}
              {#if event.data.attendees && event.data.attendees.length > 0}
                <div class="mt-1 flex flex-wrap gap-x-1.5 gap-y-0.5">
                  {#if event.data.minister && event.data.minister.id !== actor.id}
                    <a href="/person/{event.data.minister.id}" class="text-[11px] font-display font-semibold whitespace-nowrap hover:text-accent transition-colors">{event.data.minister.name},</a>
                  {/if}
                  {#each event.data.attendees.filter((a: any) => a.actor?.id !== actor.id) as attendee, i}
                    {@const remaining = event.data.attendees.filter((a: any) => a.actor?.id !== actor.id)}
                    {#if attendee.actor?.id}
                      <a href="/person/{attendee.actor.id}" class="text-[11px] font-display font-semibold whitespace-nowrap hover:text-accent transition-colors">{attendee.actor_name_raw || attendee.actor.name}{i < remaining.length - 1 ? ',' : ''}</a>
                    {:else}
                      <span class="text-[11px] font-display font-semibold whitespace-nowrap">{attendee.actor_name_raw || 'Unknown'}{i < remaining.length - 1 ? ',' : ''}</span>
                    {/if}
                  {/each}
                </div>
              {:else}
                <p class="text-[11px] font-display font-semibold mt-1">
                  {#if event.data.minister && event.data.minister.id !== actor.id}
                    <a href="/person/{event.data.minister.id}" class="hover:text-accent transition-colors">{event.data.minister.name}</a> —
                  {/if}
                  {event.data.organisation_met_raw || 'Unknown'}
                </p>
              {/if}
              {#if event.data.department}
                <span class="meta-text block mt-0.5">{event.data.department.name}</span>
              {/if}
            </div>
          </div>
        {/each}
      {/if}

      <!-- Consultancies: summary or individual -->
      {#if group.consultancies.length > COLLAPSE_THRESHOLD && !expandedConsultancies.has(group.year)}
        <!-- Collapsed consultancy summary -->
        <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleConsultancies(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleConsultancies(group.year); } }}>
          <div class="timeline-date">
            <span class="date-text">{group.consultancies.length} {isOrg && group.consultancies[0]?.data.agency?.id === actor.id ? 'clients' : 'consultancies'}</span>
          </div>
          <div class="timeline-content consultancy-border summary-content">
            <div class="flex items-baseline justify-between gap-4 mb-2">
              <div>
                <span class="font-display font-bold">{group.consultancies.length} {isOrg && group.consultancies[0]?.data.agency?.id === actor.id ? 'clients' : 'consultancies'}</span>
                <span class="meta-text ml-2">with {group.topClients.length} {isOrg && group.consultancies[0]?.data.agency?.id === actor.id ? (group.topClients.length === 1 ? 'organisation' : 'organisations') : (group.topClients.length === 1 ? 'agency' : 'agencies')}</span>
              </div>
              <span class="expand-label">Show all {group.consultancies.length} ▸</span>
            </div>
            <svg class="year-bar" aria-hidden="true">
              <rect x="0" y="0" width="100%" height="100%" fill="#1a1a1a" fill-opacity="0.03"/>
              <rect x="0" y="0" width="{(group.consultancies.length / maxConsultancyCount) * 100}%" height="100%" fill="url(#hatch-consultancy-year)"/>
            </svg>
            <div class="space-y-1 mt-2">
              {#each group.topClients.slice(0, 5) as client}
                <div class="flex items-baseline justify-between gap-2 min-w-0">
                  {#if client.id}
                    <a href="/person/{client.id}" class="text-[11px] truncate min-w-0 hover:text-accent transition-colors" title={client.name}>{client.name}</a>
                  {:else}
                    <span class="text-[11px] truncate min-w-0" title={client.name}>{client.name}</span>
                  {/if}
                  <span class="text-[10px] text-ink-muted shrink-0 tabular">{client.count} {client.count === 1 ? 'engagement' : 'engagements'}</span>
                </div>
              {/each}
              {#if group.topClients.length > 5}
                <p class="text-[10px] text-ink-muted">+ {group.topClients.length - 5} more</p>
              {/if}
            </div>
          </div>
        </div>

      {:else if group.consultancies.length > 0}
        <!-- Individual consultancies (or expanded) -->
        {#if group.consultancies.length > COLLAPSE_THRESHOLD}
          <div class="timeline-row summary-row clickable-row" role="button" tabindex="0" onclick={(e) => { if ((e.target as HTMLElement).closest('a')) return; toggleConsultancies(group.year); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleConsultancies(group.year); } }}>
            <div class="timeline-date">
              <span class="date-text">{group.consultancies.length} {isOrg && group.consultancies[0]?.data.agency?.id === actor.id ? 'clients' : 'consultancies'}</span>
            </div>
            <div class="timeline-content consultancy-border summary-content">
              <div class="flex items-baseline justify-between gap-4">
                <div>
                  <span class="font-display font-bold">{group.consultancies.length} {isOrg && group.consultancies[0]?.data.agency?.id === actor.id ? 'clients' : 'consultancies'}</span>
                </div>
                <span class="expand-label">Collapse ▾</span>
              </div>
            </div>
          </div>
        {/if}
        {#each group.consultancies as event}
          {@const isAgency = event.data.agency?.id === actor.id}
          {@const counterparty = isAgency ? event.data.client : event.data.agency}
          {@const roleLabel = isAgency ? 'Client' : 'Consultancy'}
          <div class="timeline-row">
            <div class="timeline-date">
              <span class="date-text">{formatDateRange(event.data.start_date, event.data.end_date)}</span>
            </div>
            <div class="timeline-content consultancy-border">
              {#if counterparty?.id}
                <a href="/person/{counterparty.id}" class="font-display font-semibold hover:text-accent transition-colors">{counterparty.name}</a>
              {:else}
                <span class="font-display font-semibold">{counterparty?.name || 'Unknown'}</span>
              {/if}
              <span class="meta-text ml-2">{event.data.label && event.data.label !== 'Consultancy' ? event.data.label : roleLabel}</span>
            </div>
          </div>
        {/each}
      {/if}
    {/each}

    <!-- Event count -->
    {#if isLazyMode}
      {@const lazyTotal = yearlyTotals?.reduce((sum: number, yt: any) => sum + (yt.count || 0), 0) || 0}
      <div class="mt-6 text-center">
        <p class="text-xs text-ink-muted">
          {lazyTotal.toLocaleString()} donations across {yearGroups.length} years — click a year to load details.
        </p>
      </div>
    {:else if totalEvents > donations.results.length + donationsMade.results.length + meetings.results.length}
      <div class="mt-6 text-center">
        <p class="text-xs text-ink-muted">
          Showing {donations.results.length + donationsMade.results.length + meetings.results.length + memberships.results.length} of {totalEvents + memberships.count} events.
        </p>
      </div>
    {/if}
  </div>
{/if}

<style>
  .timeline {
    position: relative;
    padding-left: 1px;
    overflow-x: hidden;
  }

  .timeline::before {
    content: '';
    position: absolute;
    left: 160px;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(26, 26, 26, 0.08);
  }

  .year-marker {
    position: relative;
    padding: 1.5rem 0 0.5rem 0;
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
  }

  .year-label {
    font-family: 'Zodiak', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: #1a1a1a;
    padding-left: 176px;
    flex-shrink: 0;
  }

  /* GN2: plate rule extending from year text to right edge */
  .plate-rule {
    flex: 1;
    height: 1px;
    background-color: rgba(26, 26, 26, 0.12);
    align-self: center;
    margin-top: 0.3em;
  }

  /* GN3: margin activity glyphs in left date gutter */
  .year-glyphs {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 160px;
    text-align: right;
    padding-right: 1.25rem;
    font-size: 11px;
    letter-spacing: 0.2em;
    line-height: 1;
    pointer-events: none;
    user-select: none;
  }

  .year-glyphs .glyph {
    display: inline-block;
    margin-left: 0.15em;
  }

  .timeline-row {
    display: grid;
    grid-template-columns: 160px minmax(0, 1fr);
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid rgba(26, 26, 26, 0.04);
    position: relative;
  }

  .timeline-date {
    text-align: right;
    padding-right: 1.25rem;
    padding-top: 0.125rem;
  }

  .date-text {
    font-size: 0.625rem;
    color: #6b6b6b;
  }

  .role-context {
    display: block;
    font-size: 0.5625rem;
    color: #6b6b6b;
    margin-top: 0.125rem;
  }

  .meta-text {
    font-size: 0.625rem;
    color: #6b6b6b;
  }

  .timeline-content {
    padding-left: 1.25rem;
    border-left: 3px solid transparent;
    position: relative;
  }

  /* GN1: specimen dot sits on the spine (≈160px) for each event, halo lifts it off the spine line */
  .timeline-content::before {
    content: '';
    position: absolute;
    left: -20px;
    top: 0.9em;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--dot-color, transparent);
    box-shadow: 0 0 0 2px #FAF9F6;
    pointer-events: none;
  }

  /* Type borders + specimen dot colors */
  .role-content {
    border-left-color: #C54B3C;
    background: rgba(197, 75, 60, 0.03);
    padding: 0.5rem 0.75rem 0.5rem 1.25rem;
    --dot-color: #C54B3C;
  }

  .donation-border { border-left-color: #5B7355; --dot-color: #5B7355; }
  .donated-border { border-left-color: #B87333; --dot-color: #B87333; }
  .meeting-border { border-left-color: #4A7BA7; --dot-color: #4A7BA7; }
  .consultancy-border { border-left-color: #DAA520; --dot-color: #DAA520; }

  /* Summary rows */
  .summary-content {
    background: rgba(26, 26, 26, 0.015);
    padding: 0.75rem 1rem 0.75rem 1.25rem;
    overflow: hidden;
  }

  /* GN9: hatched proportional year-bar under collapsed summaries */
  .year-bar {
    display: block;
    width: 100%;
    height: 6px;
    margin-top: 0.25rem;
  }

  .clickable-row {
    width: 100%;
    max-width: 100%;
    text-align: left;
    background: none;
    border: none;
    border-bottom: 1px solid rgba(26, 26, 26, 0.04);
    cursor: pointer;
    transition: background 0.15s;
    overflow: hidden;
  }

  .clickable-row:hover {
    background: rgba(26, 26, 26, 0.02);
  }

  .clickable-row:focus-visible {
    outline: 2px solid #C54B3C;
    outline-offset: -2px;
  }

  .clickable-row:hover .expand-label {
    color: #1a1a1a;
  }

  .expand-label {
    font-family: 'Satoshi', sans-serif;
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #C54B3C;
    white-space: nowrap;
  }

  .type-badge {
    display: inline-block;
    margin-left: 0.5rem;
    font-family: 'Satoshi', sans-serif;
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6b6b6b;
  }

  @media (max-width: 768px) {
    .timeline::before {
      left: 0;
    }

    .year-label {
      padding-left: 1rem;
    }

    .timeline-row {
      grid-template-columns: 1fr;
      gap: 0.25rem;
      padding-left: 0.75rem;
      padding-right: 0.75rem;
    }

    .clickable-row {
      padding-left: 0.75rem;
      padding-right: 0.75rem;
    }

    .timeline-date {
      text-align: left;
      padding-right: 0;
    }

    .timeline-content {
      padding-left: 0.75rem;
    }

    .summary-content {
      padding-right: 0.75rem;
    }

    /* GN1 specimen dots: hide on mobile — date gutter collapses, dot has nowhere sensible to sit */
    .timeline-content::before {
      display: none;
    }

    /* GN3 glyphs: inline alongside the year label on mobile (date gutter is gone) */
    .year-glyphs {
      position: static;
      width: auto;
      text-align: left;
      padding: 0 0 0 0.25rem;
      transform: none;
      order: 2;
    }

    .year-marker {
      align-items: center;
    }
  }
</style>
