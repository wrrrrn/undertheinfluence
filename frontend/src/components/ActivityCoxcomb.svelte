<script lang="ts">
  interface YearCount {
    year: number | string;
    count: number;
  }

  interface Props {
    donations?: YearCount[];
    meetings?: YearCount[];
    size?: number;
    donationColor?: string;
    meetingColor?: string;
    showAxis?: boolean;
    name?: string;
    label?: string;
    donationLabel?: string;
  }

  let {
    donations = [],
    meetings = [],
    size = 220,
    donationColor = '#5B7355',
    meetingColor = '#4A7BA7',
    showAxis = true,
    name = 'this actor',
    label,
    donationLabel = 'donations received',
  }: Props = $props();

  function pluralize(n: number, word: string): string {
    return n === 1 ? word : `${word}s`;
  }

  function toYearInt(v: number | string): number | null {
    const n = typeof v === 'number' ? v : parseInt(v, 10);
    return Number.isNaN(n) ? null : n;
  }

  const donationCounts = new Map<number, number>();
  for (const d of donations) {
    const y = toYearInt(d.year);
    if (y !== null && d.count > 0) donationCounts.set(y, (donationCounts.get(y) || 0) + d.count);
  }
  const meetingCounts = new Map<number, number>();
  for (const m of meetings) {
    const y = toYearInt(m.year);
    if (y !== null && m.count > 0) meetingCounts.set(y, (meetingCounts.get(y) || 0) + m.count);
  }

  const allYears = [...donationCounts.keys(), ...meetingCounts.keys()];
  const minYear = allYears.length > 0 ? Math.min(...allYears) : 2000;
  const maxYear = allYears.length > 0 ? Math.max(...allYears) : 2026;

  const maxDonations = Math.max(1, ...Array.from(donationCounts.values()));
  const maxMeetings = Math.max(1, ...Array.from(meetingCounts.values()));

  const yearRange = Array.from({ length: maxYear - minYear + 1 }, (_, i) => minYear + i);
  const n = yearRange.length;

  const legendHeight = 16;
  const axisLabelHeight = showAxis ? 10 : 0;
  const ringTop = legendHeight;
  const ringBottom = size - axisLabelHeight;
  const cx = size / 2;
  const cy = (ringTop + ringBottom) / 2;
  const R = Math.min(cx, (ringBottom - ringTop) / 2) - 3;
  const TWO_PI = Math.PI * 2;
  const wedgeAngle = TWO_PI / n;

  function wedgePath(idx: number, count: number, maxVal: number): string {
    if (count === 0) return '';
    const r = R * Math.sqrt(count / maxVal);
    const a0 = -Math.PI / 2 + idx * wedgeAngle;
    const a1 = a0 + wedgeAngle;
    const x0 = cx + r * Math.cos(a0);
    const y0 = cy + r * Math.sin(a0);
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy + r * Math.sin(a1);
    return `M ${cx.toFixed(2)},${cy.toFixed(2)} L ${x0.toFixed(2)},${y0.toFixed(2)} A ${r.toFixed(2)},${r.toFixed(2)} 0 0 1 ${x1.toFixed(2)},${y1.toFixed(2)} Z`;
  }

  const wedges = yearRange.map((y, i) => {
    const dCount = donationCounts.get(y) || 0;
    const mCount = meetingCounts.get(y) || 0;
    const dRadius = dCount === 0 ? 0 : R * Math.sqrt(dCount / maxDonations);
    const mRadius = mCount === 0 ? 0 : R * Math.sqrt(mCount / maxMeetings);
    return {
      idx: i,
      year: y,
      dCount,
      mCount,
      dPath: wedgePath(i, dCount, maxDonations),
      mPath: wedgePath(i, mCount, maxMeetings),
      donationOnTop: mRadius > dRadius,
    };
  });

  const donationPatternId = $derived(`cox-stip-d-${donationColor.replace('#', '')}`);
  const meetingPatternId = $derived(`cox-stip-m-${meetingColor.replace('#', '')}`);

  const hasData = donationCounts.size > 0 || meetingCounts.size > 0;

  // --- CF1: a11y summary data ---
  const donationValues = Array.from(donationCounts.values());
  const meetingValues = Array.from(meetingCounts.values());
  const totalDonations = donationValues.reduce((a, b) => a + b, 0);
  const totalMeetings = meetingValues.reduce((a, b) => a + b, 0);
  const donationYears = donationCounts.size;
  const meetingYears = meetingCounts.size;

  function peakFor(m: Map<number, number>): { year: number; count: number } | null {
    let best: { year: number; count: number } | null = null;
    for (const [y, c] of m.entries()) {
      if (!best || c > best.count) best = { year: y, count: c };
    }
    return best;
  }
  const peakDonation = peakFor(donationCounts);
  const peakMeeting = peakFor(meetingCounts);

  function median(values: number[]): number {
    if (values.length === 0) return 0;
    const s = [...values].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  }
  const medianDonations = median(donationValues);

  // --- CF2: peak-year leader line geometry ---
  // Only draw when there's a clear peak (>= 5× median and at least 3 years of data).
  const peakWedge = (
    peakDonation &&
    donationYears >= 3 &&
    medianDonations > 0 &&
    peakDonation.count >= 5 * medianDonations
  )
    ? wedges.find(w => w.year === peakDonation.year && w.dCount > 0) || null
    : null;

  // Leader-dot marks the peak wedge in the chart; the verbal caption lives in
  // the marginalia dl next to the coxcomb, so no text is rendered inside the
  // SVG (keeps the annotation legible regardless of which quadrant the peak
  // lands in, and avoids overflow into the section padding).
  const peakGeometry = peakWedge ? (() => {
    const angle = -Math.PI / 2 + (peakWedge.idx + 0.5) * wedgeAngle;
    const r = R * Math.sqrt(peakWedge.dCount / maxDonations);
    const x1 = cx + r * Math.cos(angle);
    const y1 = cy + r * Math.sin(angle);
    const x2 = cx + (R - 2) * Math.cos(angle);
    const y2 = cy + (R - 2) * Math.sin(angle);
    return { x1, y1, x2, y2 };
  })() : null;

  const uid = $props.id();
  const titleId = `cox-title-${uid}`;
  const descId = `cox-desc-${uid}`;
  const headline = $derived(label ?? `Activity shape for ${name}, ${minYear}–${maxYear}`);
</script>

{#if hasData}
  <svg
    width={size} height={size} viewBox="0 0 {size} {size}"
    class="coxcomb"
    role="img"
    aria-labelledby="{titleId} {descId}"
  >
    <title id={titleId}>{headline}</title>
    <desc id={descId}>
      {donationLabel.charAt(0).toUpperCase() + donationLabel.slice(1)} and ministerial meetings each year.
      {totalDonations} {pluralize(totalDonations, 'donation')} across {donationYears} {pluralize(donationYears, 'year')}.
      {totalMeetings} {pluralize(totalMeetings, 'meeting')} across {meetingYears} {pluralize(meetingYears, 'year')}.
      {#if peakDonation}Peak donation year: {peakDonation.year} ({peakDonation.count}).{/if}
      {#if peakMeeting} Peak meeting year: {peakMeeting.year} ({peakMeeting.count}).{/if}
    </desc>
    <defs>
      <pattern id={donationPatternId} width="4" height="4" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="0.6" fill={donationColor} fill-opacity="0.55"/>
        <circle cx="3" cy="3" r="0.5" fill={donationColor} fill-opacity="0.4"/>
      </pattern>
      <pattern id={meetingPatternId} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="4" stroke={meetingColor} stroke-width="0.9" stroke-opacity="0.42"/>
      </pattern>
    </defs>

    <!-- Inline legend -->
    <g font-family="Satoshi, sans-serif" font-size="8.5" fill="#4a4a4a">
      <rect x={cx - 96} y="2" width="10" height="10" fill="url(#{donationPatternId})" stroke={donationColor} stroke-width="0.5" stroke-opacity="0.8"/>
      <text x={cx - 82} y="10.5">{donationLabel}</text>
      <rect x={cx + 22} y="2" width="10" height="10" fill="url(#{meetingPatternId})" stroke={meetingColor} stroke-width="0.6" stroke-opacity="0.8"/>
      <text x={cx + 36} y="10.5">meetings</text>
    </g>

    <!-- Specimen plate boundary -->
    <circle cx={cx} cy={cy} r={R} fill="none" stroke="#1a1a1a" stroke-width="0.4" stroke-opacity="0.12"/>
    <circle cx={cx} cy={cy} r={R * 0.5} fill="none" stroke="#1a1a1a" stroke-width="0.3" stroke-opacity="0.08" stroke-dasharray="1 2"/>

    <!-- Wedges -->
    {#each wedges as w}
      {#if w.donationOnTop}
        {#if w.mCount > 0}
          <path d={w.mPath} fill="url(#{meetingPatternId})" stroke={meetingColor} stroke-width="0.5" stroke-opacity="0.75" style="mix-blend-mode: multiply"/>
        {/if}
        {#if w.dCount > 0}
          <path d={w.dPath} fill="url(#{donationPatternId})" stroke={donationColor} stroke-width="0.5" stroke-opacity="0.8"/>
        {/if}
      {:else}
        {#if w.dCount > 0}
          <path d={w.dPath} fill="url(#{donationPatternId})" stroke={donationColor} stroke-width="0.5" stroke-opacity="0.8"/>
        {/if}
        {#if w.mCount > 0}
          <path d={w.mPath} fill="url(#{meetingPatternId})" stroke={meetingColor} stroke-width="0.5" stroke-opacity="0.75" style="mix-blend-mode: multiply"/>
        {/if}
      {/if}
    {/each}

    <!-- CF2: Peak-year marker — leader-dot on the wedge, caption lives in the marginalia -->
    {#if peakGeometry}
      <line
        x1={peakGeometry.x1} y1={peakGeometry.y1}
        x2={peakGeometry.x2} y2={peakGeometry.y2}
        stroke="#C54B3C" stroke-width="0.8" stroke-opacity="0.6"
      />
      <circle cx={peakGeometry.x2} cy={peakGeometry.y2} r="2.2" fill="#C54B3C"/>
    {/if}

    {#if showAxis}
      <text x={cx} y={size - 1} text-anchor="middle" font-size="8" fill="#6b6b6b" font-family="Satoshi, sans-serif">
        {minYear}–{maxYear}
      </text>
    {/if}
  </svg>
{/if}

<style>
  .coxcomb {
    display: block;
    overflow: visible;
  }
</style>
