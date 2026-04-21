<script lang="ts">
  import { forceSimulation, forceCollide, forceX, forceY } from 'd3-force';
  import { scaleSqrt } from 'd3-scale';
  import { onMount } from 'svelte';

  interface Props {
    donations: Array<{ value: number | string }>;
    width?: number;
    height?: number;
    color?: string;
  }

  let { donations, width = 200, height = 72, color = '#5B7355' }: Props = $props();

  const values = donations
    .map(d => parseFloat(d.value as string) || 0)
    .filter(v => v > 0);
  const maxVal = Math.max(...values, 1);

  const rScale = scaleSqrt().domain([0, maxVal]).range([1.2, Math.min(12, Math.max(6, height / 8))]);

  // Initial positions — scattered near centre, visible immediately, refined after mount.
  let nodes = $state(values.map(v => ({
    value: v,
    r: rScale(v),
    x: width / 2 + (Math.random() - 0.5) * Math.min(width * 0.6, 40),
    y: height / 2 + (Math.random() - 0.5) * Math.min(height * 0.6, 20),
  })));

  onMount(() => {
    const simulation = forceSimulation(nodes)
      .force('x', forceX(width / 2).strength(0.12))
      .force('y', forceY(height / 2).strength(0.22))
      .force('collide', forceCollide((d: any) => d.r + 0.6))
      .stop();

    for (let i = 0; i < 120; i++) simulation.tick();

    nodes = nodes.map(n => ({
      ...n,
      x: Math.max(n.r + 1, Math.min(width - n.r - 1, n.x)),
      y: Math.max(n.r + 1, Math.min(height - n.r - 1, n.y)),
    }));
  });
</script>

{#if nodes.length > 0}
  <svg {width} {height} viewBox="0 0 {width} {height}" class="concentration" aria-hidden="true">
    {#each nodes as node}
      <circle
        cx={node.x}
        cy={node.y}
        r={node.r}
        fill={color}
        fill-opacity="0.5"
        stroke={color}
        stroke-width="0.6"
        stroke-opacity="0.85"
      />
    {/each}
  </svg>
{/if}

<style>
  .concentration {
    display: block;
    overflow: hidden;
  }
</style>
