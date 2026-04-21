<script lang="ts">
  import { scaleLinear } from 'd3-scale';

  interface Props {
    years: number[];
    width?: number;
    height?: number;
    color?: string;
    showAxis?: boolean;
  }

  let { years, width = 200, height = 44, color = '#5B7355', showAxis = true }: Props = $props();

  const validYears = years.filter(y => typeof y === 'number' && !isNaN(y));
  const minYear = validYears.length > 0 ? Math.min(...validYears) : 2000;
  const maxYear = validYears.length > 0 ? Math.max(...validYears) : 2026;

  // Aggregate: count events per year
  const yearCounts = new Map<number, number>();
  validYears.forEach(y => yearCounts.set(y, (yearCounts.get(y) || 0) + 1));
  const maxCount = Math.max(1, ...Array.from(yearCounts.values()));

  const padding = 6;
  const axisLabelHeight = showAxis ? 10 : 0;
  const baselineY = height - axisLabelHeight - 2;
  const plotTop = 3;
  const plotHeight = baselineY - plotTop;

  // Fill every year in the range (zero if no events) so the area reads as a continuous record
  const yearRange = Array.from({ length: maxYear - minYear + 1 }, (_, i) => minYear + i);

  const xScale = scaleLinear()
    .domain([minYear, maxYear + 1]) // +1 so the last year bucket extends to the right edge
    .range([padding, width - padding]);

  const yScale = (count: number) => baselineY - (count / maxCount) * plotHeight;

  // Build step-after polygon: for each year bucket, draw a flat top at its count value
  // extending from that year's x to the next year's x, then step to the next value.
  const points = yearRange.map(y => ({
    year: y,
    count: yearCounts.get(y) || 0,
    x0: xScale(y),
    x1: xScale(y + 1),
    y: yScale(yearCounts.get(y) || 0),
  }));

  let d = `M ${padding},${baselineY}`;
  points.forEach(p => {
    d += ` L ${p.x0},${p.y} L ${p.x1},${p.y}`;
  });
  d += ` L ${width - padding},${baselineY} Z`;

  // Stipple pattern id — unique per color so multiple components don't collide
  const patternId = `stipple-${color.replace('#', '')}`;
</script>

{#if validYears.length > 0}
  <svg {width} {height} viewBox="0 0 {width} {height}" class="activity-area" aria-hidden="true">
    <defs>
      <pattern id={patternId} width="5" height="5" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="0.7" fill={color} fill-opacity="0.55"/>
        <circle cx="3.5" cy="3.5" r="0.55" fill={color} fill-opacity="0.4"/>
      </pattern>
    </defs>
    <!-- Track background at the plot height — shows the "plate" extent -->
    <rect x={padding} y={plotTop} width={width - padding * 2} height={plotHeight}
          fill="#1a1a1a" fill-opacity="0.02"/>
    <!-- Stippled area -->
    <path {d} fill="url(#{patternId})" stroke={color} stroke-width="0.6" stroke-opacity="0.7"/>
    {#if showAxis}
      <line x1={padding} y1={baselineY} x2={width - padding} y2={baselineY}
            stroke="#1a1a1a" stroke-width="0.5" opacity="0.2"/>
      <text x={padding} y={height - 1} font-size="8" fill="#6b6b6b" font-family="Satoshi, sans-serif">{minYear}</text>
      <text x={width - padding} y={height - 1} text-anchor="end" font-size="8" fill="#6b6b6b" font-family="Satoshi, sans-serif">{maxYear}</text>
    {/if}
  </svg>
{/if}

<style>
  .activity-area {
    display: block;
    overflow: hidden;
  }
</style>
