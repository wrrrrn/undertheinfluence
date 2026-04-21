<script lang="ts">
  interface Props {
    actor: any;
    donations: any;
    donationsMade: any;
    memberships: any;
    meetings: any;
    consultancies: any;
  }

  let {
    actor,
    donations,
    donationsMade,
    memberships,
    meetings,
    consultancies,
  }: Props = $props();

  // Determine which tabs to show
  const tabs: { id: string; label: string; count: number }[] = [];
  if (donations.count > 0) tabs.push({ id: 'received', label: 'Donations Received', count: donations.count });
  if (donationsMade.count > 0) tabs.push({ id: 'made', label: 'Donations Made', count: donationsMade.count });
  if (meetings.count > 0) tabs.push({ id: 'meetings', label: 'Meetings', count: meetings.count });
  if (consultancies.count > 0) tabs.push({ id: 'consultancies', label: 'Lobbying', count: consultancies.count });
  if (memberships.count > 0) tabs.push({ id: 'memberships', label: 'Roles', count: memberships.count });

  let activeTab = $state(tabs.length > 0 ? tabs[0].id : '');

  function formatCurrency(value: string | number): string {
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (num >= 1_000_000_000) return `£${(num / 1_000_000_000).toFixed(1)}bn`;
    if (num >= 1_000_000) return `£${(num / 1_000_000).toFixed(1)}m`;
    if (num >= 1_000) return `£${(num / 1_000).toFixed(0)}k`;
    return `£${num.toLocaleString()}`;
  }

  function formatDate(date: string | null): string {
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
</script>

{#if tabs.length === 0}
  <p class="text-ink-muted italic mt-8">No data available for this actor.</p>
{:else}
  <!-- Tab Navigation -->
  <div class="flex gap-0 border-b border-ink/10 mt-8" role="tablist">
    {#each tabs as tab}
      <button
        role="tab"
        aria-selected={activeTab === tab.id}
        class="tab-button"
        class:active={activeTab === tab.id}
        onclick={() => activeTab = tab.id}
      >
        {tab.label}
        <span class="tab-count">{tab.count}</span>
      </button>
    {/each}
  </div>

  <!-- Tab Content -->
  <div class="mt-6" role="tabpanel">
    {#if activeTab === 'received'}
      <div class="space-y-0">
        {#each donations.results as donation}
          <div class="donation-row">
            <div class="flex items-baseline justify-between gap-4">
              <div class="min-w-0">
                <a href="/person/{donation.donor.id}" class="font-display font-semibold hover:text-accent transition-colors">
                  {donation.donor.name}
                </a>
                {#if donation.donation_type}
                  <span class="text-[10px] text-ink-muted ml-2 uppercase tracking-wider">{donation.donation_type}</span>
                {/if}
              </div>
              <span class="font-display font-bold text-lg tabular shrink-0">
                {formatCurrency(donation.value)}
              </span>
            </div>
            <div class="flex gap-4 text-[10px] text-ink-muted mt-1">
              {#if donation.accepted_date}
                <span>{formatDate(donation.accepted_date)}</span>
              {/if}
              {#if donation.purpose_of_visit}
                <span class="truncate">{donation.purpose_of_visit}</span>
              {/if}
            </div>
            {#if donation.donor_key_people && donation.donor_key_people.length > 0}
              <div class="text-[9px] text-ink-muted mt-1 pl-2 border-l-2 border-accent/20">
                {donation.donor_key_people.map((p: any) => `${p.name} (${p.role})`).join(' · ')}
              </div>
            {/if}
          </div>
        {/each}
        {#if donations.count > donations.results.length}
          <p class="text-xs text-ink-muted italic mt-4">
            Showing {donations.results.length} of {donations.count} donations.
          </p>
        {/if}
      </div>

    {:else if activeTab === 'made'}
      <div class="space-y-0">
        {#each donationsMade.results as donation}
          <div class="donation-row">
            <div class="flex items-baseline justify-between gap-4">
              <div class="min-w-0">
                <a href="/person/{donation.recipient.id}" class="font-display font-semibold hover:text-accent transition-colors">
                  {donation.recipient.name}
                </a>
                {#if donation.donation_type}
                  <span class="text-[10px] text-ink-muted ml-2 uppercase tracking-wider">{donation.donation_type}</span>
                {/if}
              </div>
              <span class="font-display font-bold text-lg tabular shrink-0">
                {formatCurrency(donation.value)}
              </span>
            </div>
            <div class="flex gap-4 text-[10px] text-ink-muted mt-1">
              {#if donation.accepted_date}
                <span>{formatDate(donation.accepted_date)}</span>
              {/if}
              {#if donation.purpose_of_visit}
                <span class="truncate">{donation.purpose_of_visit}</span>
              {/if}
            </div>
          </div>
        {/each}
        {#if donationsMade.count > donationsMade.results.length}
          <p class="text-xs text-ink-muted italic mt-4">
            Showing {donationsMade.results.length} of {donationsMade.count} donations.
          </p>
        {/if}
      </div>

    {:else if activeTab === 'meetings'}
      <div class="space-y-0">
        {#each meetings.results as meeting}
          <div class="donation-row">
            <div class="flex items-baseline justify-between gap-4">
              <div class="min-w-0">
                <span class="font-display font-semibold">{meeting.organisation_met_raw || 'Unknown'}</span>
                {#if meeting.department}
                  <span class="text-[10px] text-ink-muted ml-2">{meeting.department.name}</span>
                {/if}
              </div>
              <span class="text-sm text-ink-muted tabular shrink-0">{formatDate(meeting.meeting_date)}</span>
            </div>
            {#if meeting.purpose}
              <p class="text-[11px] text-ink-light mt-1 leading-relaxed">{meeting.purpose}</p>
            {/if}
            {#if meeting.attendees && meeting.attendees.length > 0}
              <div class="text-[9px] text-ink-muted mt-1 pl-2 border-l-2 border-accent/20">
                {#each meeting.attendees as attendee, i}
                  {#if attendee.actor?.id}
                    <a href="/person/{attendee.actor.id}" class="hover:text-accent transition-colors">{attendee.actor_name_raw || attendee.actor.name}</a>{#if i < meeting.attendees.length - 1} · {/if}
                  {:else}
                    {attendee.actor_name_raw || 'Unknown'}{#if i < meeting.attendees.length - 1} · {/if}
                  {/if}
                {/each}
              </div>
            {/if}
          </div>
        {/each}
        {#if meetings.count > meetings.results.length}
          <p class="text-xs text-ink-muted italic mt-4">
            Showing {meetings.results.length} of {meetings.count} meetings.
          </p>
        {/if}
      </div>

    {:else if activeTab === 'consultancies'}
      <div class="space-y-0">
        {#each consultancies.results as consultancy}
          <div class="donation-row">
            <div class="flex items-baseline justify-between gap-4">
              <div class="min-w-0">
                {#if consultancy.agency?.id}
                  <a href="/person/{consultancy.agency.id}" class="font-display font-semibold hover:text-accent transition-colors">{consultancy.agency.name}</a>
                {:else if consultancy.client?.id}
                  <a href="/person/{consultancy.client.id}" class="font-display font-semibold hover:text-accent transition-colors">{consultancy.client.name}</a>
                {:else}
                  <span class="font-display font-semibold">{consultancy.agency?.name || consultancy.client?.name || 'Unknown'}</span>
                {/if}
                {#if consultancy.label}
                  <span class="text-[10px] text-ink-muted ml-2">{consultancy.label}</span>
                {/if}
              </div>
              <span class="text-[10px] text-ink-muted shrink-0">
                {formatDate(consultancy.start_date)} — {consultancy.end_date ? formatDate(consultancy.end_date) : 'Present'}
              </span>
            </div>
          </div>
        {/each}
        {#if consultancies.count > consultancies.results.length}
          <p class="text-xs text-ink-muted italic mt-4">
            Showing {consultancies.results.length} of {consultancies.count} consultancy relationships.
          </p>
        {/if}
      </div>

    {:else if activeTab === 'memberships'}
      <div class="space-y-0">
        {#each memberships.results as membership}
          <div class="donation-row">
            <div class="flex items-baseline justify-between gap-4">
              <div class="min-w-0">
                <span class="font-display font-semibold">{membership.role || 'Member'}</span>
                {#if membership.organization}
                  <span class="text-[10px] text-ink-muted ml-2">{membership.organization.name}</span>
                {/if}
              </div>
              <span class="text-[10px] text-ink-muted shrink-0">
                {formatDate(membership.start_date)} — {membership.end_date ? formatDate(membership.end_date) : 'Present'}
              </span>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .tab-button {
    padding: 0.75rem 1.25rem;
    font-family: 'Satoshi', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6b6b6b;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    background: none;
    border-top: none;
    border-left: none;
    border-right: none;
  }

  .tab-button:hover {
    color: #1a1a1a;
  }

  .tab-button.active {
    color: #C54B3C;
    border-bottom-color: #C54B3C;
  }

  .tab-count {
    display: inline-block;
    margin-left: 0.375rem;
    font-size: 0.625rem;
    color: #6b6b6b;
    font-variant-numeric: tabular-nums;
  }

  .tab-button.active .tab-count {
    color: #C54B3C;
  }

  .donation-row {
    padding: 0.875rem 0;
    border-bottom: 1px solid rgba(26, 26, 26, 0.05);
  }

  .donation-row:last-child {
    border-bottom: none;
  }
</style>
