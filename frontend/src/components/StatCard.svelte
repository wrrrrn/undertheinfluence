<script lang="ts">
  // Svelte 5 Runes
  let { value, label, trend = null }: {
    value: string | number;
    label: string;
    trend?: number | null;
  } = $props();
</script>

<div class="card-editorial">
  <h3 class="stat-value">
    {value}
  </h3>
  <p class="stat-label">
    {label}
  </p>
  {#if trend !== null}
    <p class="mt-2 text-sm" class:text-green-600={trend > 0} class:text-red-600={trend < 0}>
      {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {Math.abs(trend)}%
    </p>
  {/if}
</div>
