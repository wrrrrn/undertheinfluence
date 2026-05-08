<script lang="ts">
  interface BreakdownRow {
    category: string;
    count: number;
    total: string;
  }

  interface Props {
    breakdown?: BreakdownRow[];
    yearRange?: string;
    name?: string;
  }

  let { breakdown = [], yearRange = '', name = 'this actor' }: Props = $props();

  function pluralize(n: number, word: string): string {
    return n === 1 ? word : `${word}s`;
  }

  function formatCurrency(n: number): string {
    if (n >= 1_000_000) return `£${(n / 1_000_000).toFixed(1)}m`;
    if (n >= 1_000) return `£${Math.round(n / 1_000)}k`;
    return `£${Math.round(n)}`;
  }

  function slug(s: string): string {
    return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  }

  // Fixed pattern/colour assignments per spec.
  type Assignment = { colour: string; patternId: string; label?: string };
  const ASSIGN: Record<string, Assignment> = {
    'Cash':                  { colour: '#5B7355', patternId: 'dtype-cash' },
    'Non Cash':              { colour: '#6B5B4F', patternId: 'dtype-noncash' },
    'Visit':                 { colour: '#B87333', patternId: 'dtype-visit' },
    'InKind':                { colour: '#7B9E87', patternId: 'dtype-inkind' },
    'Public Funds':          { colour: '#4A7BA7', patternId: 'dtype-publicfunds' },
    'Impermissible Donor':   { colour: '#6b6b6b', patternId: 'dtype-unknown' },
    'Unidentifiable Donor':  { colour: '#6b6b6b', patternId: 'dtype-unknown' },
    'Unknown':               { colour: '#4a4a4a', patternId: 'dtype-other', label: 'Unknown type' },
  };
  const OTHER: Assignment = { colour: '#4a4a4a', patternId: 'dtype-other' };

  function assign(category: string): Assignment {
    return ASSIGN[category] ?? OTHER;
  }

  // --- Normalise input ---
  const rows = $derived(
    (breakdown ?? [])
      .map(r => ({
        category: r.category,
        count: r.count,
        total: parseFloat(r.total) || 0,
      }))
      .filter(r => r.total > 0 || r.count > 0)
  );

  const totalValue = $derived(rows.reduce((a, b) => a + b.total, 0));
  const donationCount = $derived(rows.reduce((a, b) => a + b.count, 0));
  const hasData = $derived(rows.length > 0 && totalValue > 0);

  // --- Percentage rounding: largest-remainder so tiles sum to exactly 100 ---
  type PctRow = BreakdownRow & {
    total: number;
    exact: number;
    floor: number;
    rem: number;
    pct: number;
    assign: Assignment;
  };

  const pctRows: PctRow[] = $derived.by(() => {
    if (!hasData) return [];
    const raw: Omit<PctRow, 'pct'>[] = rows.map(r => {
      const exact = 100 * r.total / totalValue;
      const floor = Math.floor(exact);
      return {
        category: r.category,
        count: r.count,
        total: r.total,
        exact,
        floor,
        rem: exact - floor,
        assign: assign(r.category),
      };
    });
    const used = raw.reduce((a, b) => a + b.floor, 0);
    const toBump = 100 - used;
    const byRem = [...raw].sort((a, b) => b.rem - a.rem);
    const bumpSet = new Set<string>();
    for (let i = 0; i < toBump && i < byRem.length; i++) bumpSet.add(byRem[i].category);
    return raw.map(r => ({
      ...r,
      pct: r.floor + (bumpSet.has(r.category) ? 1 : 0),
    }));
  });

  const sortedRows: PctRow[] = $derived([...pctRows].sort((a, b) => b.total - a.total));

  // --- Tile layout (column-major, bottom-to-top, left-to-right) ---
  type Tile = { row: number; col: number; row_: PctRow };
  const tiles: Tile[] = $derived.by(() => {
    const out: Tile[] = [];
    let idx = 0;
    for (const r of sortedRows) {
      for (let i = 0; i < r.pct; i++) {
        if (idx >= 100) break;
        const col = Math.floor(idx / 10);
        const row = 9 - (idx % 10);
        out.push({ row, col, row_: r });
        idx++;
      }
      if (idx >= 100) break;
    }
    return out;
  });

  // --- Layout constants ---
  const TILE = 20;
  const TILE_INNER = 18;
  const GRID_SIZE = 10 * TILE; // 200
  const GRID_Y = 20;
  const KEY_X = GRID_SIZE + 30; // 230
  const KEY_Y = GRID_Y + 4;
  const KEY_ROW_H = 26;

  // --- Dominant category for leader line ---
  const dominant: PctRow | null = $derived(sortedRows.length > 0 ? sortedRows[0] : null);
  const dominantKeyIdx = 0;

  const dominantColCount = $derived(dominant ? Math.ceil(dominant.pct / 10) : 0);
  const dominantBlockRightX = $derived(dominant ? (dominantColCount * TILE - 2) : 0);
  const dominantBlockMidY = GRID_Y + GRID_SIZE / 2;

  const leaderX1 = KEY_X + 10 + 2;
  const leaderY1 = KEY_Y + dominantKeyIdx * KEY_ROW_H + 5;
  const leaderX2 = $derived(dominantBlockRightX);
  const leaderY2 = dominantBlockMidY;

  // --- Interaction ---
  let hovered: string | null = $state(null);

  function keyLabel(r: PctRow): string {
    return r.assign.label ?? r.category;
  }

  // uid for a11y
  const uid = $props.id();
  const titleId = `waffle-title-${uid}`;
  const descId = `waffle-desc-${uid}`;

  // Description helpers
  const dominantPct = $derived(dominant ? dominant.pct : 0);
  const secondary = $derived(sortedRows[1] ?? null);
  const remainingBlurb = $derived.by(() => {
    const remaining = sortedRows.slice(2);
    if (remaining.length === 0) return '';
    return ` Plus ${remaining.map(r => `${r.pct}% ${keyLabel(r).toLowerCase()}`).join(', ')}.`;
  });

  // --- Rendering sizes ---
  // Total viewBox width = 200 (grid) + 30 (gap) + 180 (key) = 410. Height ~240.
  const VBW = 420;
  const VBH = 240;
</script>

{#if hasData}
  <svg
    viewBox="0 0 {VBW} {VBH}"
    class="donation-type-waffle"
    role="img"
    aria-labelledby="{titleId} {descId}"
  >
    <title id={titleId}>Donation types for {name}{yearRange ? `, ${yearRange}` : ''}</title>
    <desc id={descId}>
      {formatCurrency(totalValue)} across {donationCount} {pluralize(donationCount, 'donation')}.
      {#if dominant}{dominantPct}% {keyLabel(dominant).toLowerCase()}{/if}{#if secondary}; {secondary.pct}% {keyLabel(secondary).toLowerCase()}{/if}.{remainingBlurb}
    </desc>

    <defs>
      <pattern id="dtype-cash" width="4" height="4" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="0.6" fill="#5B7355" fill-opacity="0.55"/>
        <circle cx="3" cy="3" r="0.5" fill="#5B7355" fill-opacity="0.4"/>
      </pattern>
      <pattern id="dtype-noncash" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="4" stroke="#6B5B4F" stroke-width="0.9" stroke-opacity="0.5"/>
      </pattern>
      <pattern id="dtype-visit" width="5" height="5" patternUnits="userSpaceOnUse">
        <path d="M 0,0 L 5,5 M 0,5 L 5,0" stroke="#B87333" stroke-width="0.7" stroke-opacity="0.55"/>
      </pattern>
      <pattern id="dtype-inkind" width="4" height="4" patternUnits="userSpaceOnUse">
        <line x1="0" y1="2" x2="4" y2="2" stroke="#7B9E87" stroke-width="0.8" stroke-opacity="0.55"/>
      </pattern>
      <pattern id="dtype-publicfunds" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
        <line x1="0" y1="0" x2="0" y2="4" stroke="#4A7BA7" stroke-width="1.1" stroke-opacity="0.55"/>
      </pattern>
      <pattern id="dtype-unknown" width="6" height="6" patternUnits="userSpaceOnUse">
        <circle cx="2" cy="2" r="0.5" fill="#6b6b6b" fill-opacity="0.45"/>
      </pattern>
      <pattern id="dtype-other" width="4" height="4" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="0.4" fill="#4a4a4a" fill-opacity="0.4"/>
        <circle cx="3" cy="3" r="0.4" fill="#4a4a4a" fill-opacity="0.4"/>
      </pattern>
    </defs>

    <!-- Total caption -->
    <text x="0" y="12" font-size="11" font-family="Zodiak, serif" font-weight="600" fill="#1a1a1a">
      {formatCurrency(totalValue)}
      <tspan font-family="Satoshi, sans-serif" font-weight="400" fill="#6b6b6b">
        across {donationCount} {pluralize(donationCount, 'donation')}
      </tspan>
    </text>

    <!-- 10×10 tile grid -->
    <g transform="translate(0, {GRID_Y})">
      {#each tiles as t}
        {@const dimmed = hovered !== null && hovered !== t.row_.category}
        <rect
          x={t.col * TILE} y={t.row * TILE}
          width={TILE_INNER} height={TILE_INNER}
          fill={`url(#${t.row_.assign.patternId})`}
          stroke={t.row_.assign.colour}
          stroke-width="0.4"
          stroke-opacity={hovered === t.row_.category ? 1 : 0.6}
          opacity={dimmed ? 0.35 : 1}
          data-category={t.row_.category}
          role="presentation"
          onmouseenter={() => (hovered = t.row_.category)}
          onmouseleave={() => (hovered = null)}
          class="tile"
        />
      {/each}
    </g>

    <!-- Direct-label key -->
    <g transform="translate({KEY_X}, {KEY_Y})" font-family="Satoshi, sans-serif">
      {#each sortedRows as r, i}
        {@const active = hovered === r.category}
        <g
          class="key-row"
          role="button"
          tabindex="0"
          aria-pressed={active}
          aria-label="{keyLabel(r)}: {r.pct}% of total value, {r.count} {pluralize(r.count, 'donation')}, {formatCurrency(r.total)}"
          onmouseenter={() => (hovered = r.category)}
          onmouseleave={() => (hovered = null)}
          onfocus={() => (hovered = r.category)}
          onblur={() => (hovered = null)}
        >
          {#if active}
            <rect x="-4" y={i * KEY_ROW_H - 2} width="190" height={KEY_ROW_H - 2} fill="#FAF9F6"/>
          {/if}
          <rect
            x="0" y={i * KEY_ROW_H}
            width="10" height="10"
            fill={`url(#${r.assign.patternId})`}
            stroke={r.assign.colour} stroke-width="0.4" stroke-opacity="0.8"
          />
          <text
            x="16" y={i * KEY_ROW_H + 8}
            font-size="10" fill={active ? '#C54B3C' : '#1a1a1a'}
            font-weight={active ? 600 : 400}
          >
            {keyLabel(r)}
            <tspan fill="#4a4a4a" font-weight="400">
              · {r.pct < 1 ? '<1' : r.pct}% · {r.count} {pluralize(r.count, 'donation')}
            </tspan>
          </text>
          <text
            x="16" y={i * KEY_ROW_H + 19}
            font-size="9" fill="#6b6b6b"
            font-variant-numeric="tabular-nums"
          >
            {formatCurrency(r.total)}
          </text>
        </g>
      {/each}
    </g>

    <!-- Leader line: dominant key row → dominant block in the grid -->
    {#if dominant && dominant.pct > 0}
      <line
        x1={leaderX1} y1={leaderY1}
        x2={leaderX2} y2={leaderY2}
        stroke="#6b6b6b" stroke-width="0.8" stroke-opacity="0.4"
        stroke-dasharray="2 2"
      />
      <circle cx={leaderX2} cy={leaderY2} r="2" fill="#C54B3C"/>
    {/if}

    <!-- Year anchor (echoes coxcomb) -->
    {#if yearRange}
      <text x="0" y={VBH - 2} font-size="9" fill="#6b6b6b" font-family="Satoshi, sans-serif">
        {yearRange}
      </text>
    {/if}
  </svg>
{/if}

<style>
  .donation-type-waffle {
    display: block;
    width: 100%;
    height: auto;
    max-width: 420px;
    overflow: visible;
  }
  .tile {
    transition: opacity 150ms ease, stroke-opacity 150ms ease;
  }
  .key-row {
    cursor: default;
  }
  .key-row:focus {
    outline: none;
  }
  .key-row:focus-visible > rect:first-child {
    fill: #FAF9F6;
    stroke: #C54B3C;
    stroke-width: 0.5;
  }
  @media (prefers-reduced-motion: reduce) {
    .tile {
      transition: none;
    }
  }
</style>
